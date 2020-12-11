#!/usr/bin/env python
from __future__ import unicode_literals
import argparse
import os
import re
from itertools import starmap
import multiprocessing
import pysrt
import imageio
import youtube_dl
import chardet
import nltk
import json
imageio.plugins.ffmpeg.download()
nltk.download('punkt')

from moviepy.editor import VideoFileClip, concatenate_videoclips
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from sumy.summarizers.lsa import LsaSummarizer


imageio.plugins.ffmpeg.download()


def summarize(srt_file, n_sentences, language="english"):
    # generate segmented summary
    parser = PlaintextParser.from_string(
        srt_to_txt(srt_file), Tokenizer(language))
    stemmer = Stemmer(language)
    summarizer = LsaSummarizer(stemmer)
    summarizer.stop_words = get_stop_words(language)
    segment = []
    for sentence in summarizer(parser.document, n_sentences):
        index = int(re.findall("\(([0-9]+)\)", str(sentence))[0])
        item = srt_file[index]
        segment.append(srt_segment_to_range(item))
    print(segment)
    return segment


def srt_to_txt(srt_file):
    # extract text from subtitles file
    text = ''
    for index, item in enumerate(srt_file):
        if item.text.startswith("["):
            continue
        text += "(%d) " % index
        text += item.text.replace("\n", "").strip("...").replace(
                                     ".", "").replace("?", "").replace("!", "")
        text += ". "
    
    return text
    


def srt_segment_to_range(item):
    # handling of srt segments to time range
    start_segment = item.start.hours * 60 * 60 + item.start.minutes * \
        60 + item.start.seconds + item.start.milliseconds / 1000.0
    end_segment = item.end.hours * 60 * 60 + item.end.minutes * \
        60 + item.end.seconds + item.end.milliseconds / 1000.0
    print(start_segment,end_segment)
    return start_segment, end_segment


def time_regions(regions):
    # duration of segments
    return sum(starmap(lambda start, end: end - start, regions))


def find_summary_regions(srt_filename, duration=30, language="english"):
    # find important sections
    srt_file = pysrt.open(srt_filename)

    enc = chardet.detect(open(srt_filename, "rb").read())['encoding']
    srt_file = pysrt.open(srt_filename, encoding=enc)

    # generate average subtitle duration
    subtitle_duration = time_regions(
        map(srt_segment_to_range, srt_file)) / len(srt_file)
    # compute number of sentences in the summary file
    n_sentences = duration / subtitle_duration
    summary = summarize(srt_file, n_sentences, language)
    total_time = time_regions(summary)
    too_short = total_time < duration
    if too_short:
        while total_time < duration:
            n_sentences += 1
            summary = summarize(srt_file, n_sentences, language)
            total_time = time_regions(summary)
    else:
        while total_time > duration:
            n_sentences -= 1
            summary = summarize(srt_file, n_sentences, language)
            total_time = time_regions(summary)
    return summary


def create_summary(filename, regions):
    # join segments
    subclips = []
    input_video = VideoFileClip(filename)
    last_end = 0
    for (start, end) in regions:
        subclip = input_video.subclip(start, end)
        subclips.append(subclip)
        last_end = end
    return concatenate_videoclips(subclips)

def get_summary(filename="1.mp4", subtitles="1.srt"):
    # abstract function
    regions = find_summary_regions(subtitles, 60, "english")
    summary = create_summary(filename, regions)
    base, ext = os.path.splitext(filename)
    output = "{0}_1.mp4".format(base)
    summary.to_videofile(
                output,
                codec="libx264",
                temp_audiofile="temp.m4a", remove_temp=True, audio_codec="aac")
    return output


def download_video_srt(url):
    # downloads specified Youtube video's subtitles as a vtt/srt file.
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'please_work20003.%(ext)s',
        # 'subtitlesformat': 'srt',
        'writesubtitles': True,
        # 'writeautomaticsub': True,
        # 'allsubtitles': True, # Get all subtitles
        'subtitleslangs': ['en-GB'],
        # 'listsubtitles': True
    }

    movie_filename = ""
    subtitle_filename = ""
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        # ydl.download([subs])
        # while 1:
        result = ydl.extract_info("{}".format(url), download=True)
        movie_filename = ydl.prepare_filename(result)
        subtitle_info = result.get("requested_subtitles")
            # if subtitle_info != None:
            #     break
            # else:
            #     print("contunuing\n")
            #     subtitle_info = json.loads(str({"url": "https://www.youtube.com/api/timedtext?v=K2t9gpx8mdQ&asr_langs=de%2Cen%2Ces%2Cfr%2Cit%2Cja%2Cko%2Cnl%2Cpt%2Cru&caps=asr&exp=xftt&xorp=true&xoaf=5&hl=en&ip=0.0.0.0&ipbits=0&expire=1607371373&sparams=ip%2Cipbits%2Cexpire%2Cv%2Casr_langs%2Ccaps%2Cexp%2Cxorp%2Cxoaf&signature=2931DDCF7B1751E8EA2A15555F0D141C24810D6D.84E528B05AA606FD52CCC4CC86E28047585E36CD&key=yt8&kind=asr&lang=en&tlang=af&fmt=vtt", "ext": "vtt"}))
            #     break

        # movie_filename = ydl.prepare_filename(result)

        # if subtitle_info == None:
        #     subtitle_info = {'url': 'https://www.youtube.com/api/timedtext?v=K2t9gpx8mdQ&asr_langs=de%2Cen%2Ces%2Cfr%2Cit%2Cja%2Cko%2Cnl%2Cpt%2Cru&caps=asr&exp=xftt&xorp=true&xoaf=5&hl=en&ip=0.0.0.0&ipbits=0&expire=1607371373&sparams=ip%2Cipbits%2Cexpire%2Cv%2Casr_langs%2Ccaps%2Cexp%2Cxorp%2Cxoaf&signature=2931DDCF7B1751E8EA2A15555F0D141C24810D6D.84E528B05AA606FD52CCC4CC86E28047585E36CD&key=yt8&kind=asr&lang=en&tlang=af&fmt=vtt', 'ext': 'vtt'}
        subtitle_language = list(subtitle_info.keys())[0]
        subtitle_ext = subtitle_info.get(subtitle_language).get("ext")
        subtitle_filename = movie_filename.replace(".mp4", ".%s.%s" %
                                                   (subtitle_language,
                                                    subtitle_ext))
    return movie_filename, subtitle_filename


def final(url):
    movie_filename, subtitle_filename = download_video_srt(url)
    if subtitle_filename == "":
        return "Please provide the url of a video with subtitles"
    summary_retrieval_process = multiprocessing.Process(target=get_summary, args=(movie_filename, subtitle_filename))
    summary_retrieval_process.start()
    summary_retrieval_process.join()


print(final('https://www.youtube.com/watch?v=5pEPpNpbnCI'))
    


