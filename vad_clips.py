import collections
import contextlib
import sys
import wave
import time
import webrtcvad


def read_wave(path):
    """Reads a .wav file.

    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate

def read_face_period(path, face_period):
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        face_plist = []
        for p in face_period:
            start, end = int(sample_rate * p[0] * 2), int(sample_rate * p[1] * 2)
            print("Read wav from", p[0], "to", p[1])
            face_plist.append(pcm_data[start:end-2])
        return face_plist, sample_rate


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.

    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.

    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.

    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(pid, face_period, sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.

    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.

    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.

    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.

    Arguments:

    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).

    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    start_time = 0
    end_time = 0
    voiced_frames = []
    global time_stamp
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                start_time = float(ring_buffer[0][0].timestamp)
                sys.stdout.write('\n+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            end_time = float(frame.timestamp + frame.duration)
            if num_unvoiced > 0.9 * ring_buffer.maxlen and (end_time-start_time) >= 7:
                sys.stdout.write('-(%s)\n' % (frame.timestamp + frame.duration))
                time_stamp.append([pid, face_period[pid][0]+start_time, face_period[pid][0]+end_time])
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
        end_time = float(frame.timestamp + frame.duration)
        if end_time-start_time >= 7:
            time_stamp.append([pid, face_period[pid][0]+start_time, face_period[pid][0]+end_time])
    sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])

t_start = time.time()
wav_path = "audio/apple.wav"
time_stamp = []
aggressive_para = 3
face_period = [(float(line.split()[0])/30, float(line.split()[1])/30) for line in open("face_period.txt", 'r')]
aud_list, sample_rate = read_face_period(wav_path, face_period)
vad = webrtcvad.Vad(aggressive_para)
for pid, audio in enumerate(aud_list):
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    segments = vad_collector(pid, face_period, sample_rate, 30, 300, vad, frames)
    for i, segment in enumerate(segments):
        path = 'output/clip-%002d-%002d.wav' % (pid, i)
        print(' Writing %s' % (path,))
        write_wave(path, segment, sample_rate)
output_file = 'speech_seg'
f = open(output_file, 'w')
for item in time_stamp:
    m_start, s_start = divmod(item[1], 60)
    m_end, s_end = divmod(item[2], 60)
    f.write(str(item[0])+" "+str(int(m_start))+":"+str(s_start)[:4]+"--"+str(int(m_end))+":"+str(s_end)[:4]+"\n")
f.close()
t_end = time.time()
print("Cost", str(t_end-t_start), "to get vad_clips.")

# def main(args):
#     if len(args) != 2:
#         sys.stderr.write(
#             'Usage: example.py <aggressiveness> <path to wav file>\n')
#         sys.exit(1)
#     audio, sample_rate = read_wave(args[1])
#     vad = webrtcvad.Vad(int(args[0]))
#     frames = frame_generator(30, audio, sample_rate)
#     frames = list(frames)
#     segments = vad_collector(sample_rate, 30, 150, vad, frames)
#     for i, segment in enumerate(segments):
#         path = 'output/chunk-%002d.wav' % (i,)
#         print(' Writing %s' % (path,))
#         write_wave(path, segment, sample_rate)


# if __name__ == '__main__':
#     main(sys.argv[1:])
