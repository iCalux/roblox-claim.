from .constants import DEFAULT_ID_SLACK, DEFAULT_RANGES
from .utils import find_latest_group_id
import argparse

def parse_human_number(s):
    s = s.lower()
    if s.endswith("m"):
        s = int(float(s[:-1]) * 1000000)
    elif s.endswith("k"):
        s = int(float(s[:-1]) * 1000)
    else:
        s = int(s)
    return s

def parse_range(range_string):
    start, end = range_string.split("-", 1)
    start = parse_human_number(start)
    end = parse_human_number(end)
    return (start, end)

def parse_args():
    group_id = find_latest_group_id()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w", "--workers",
        default=8,
        type=int,
        help="Number of workers",
        metavar="<num>")
    parser.add_argument(
        "-t", "--threads",
        default=50,
        type=int,
        help="Number of threads (per worker)",
        metavar="<num>")
    parser.add_argument(
        "-r", "--range",
        default=(
            *DEFAULT_RANGES,
            (DEFAULT_RANGES[-1][1] + 1, group_id + DEFAULT_ID_SLACK),
        ),
        nargs="+",
        type=parse_range,
        help="Range(s) of group IDs",
        metavar="<range>")
    parser.add_argument(
        "-p", "--proxy-file",
        required=True,
        type=argparse.FileType("r", errors="ignore"),
        help="File containing HTTP proxies", 
        metavar="<file>")
    parser.add_argument(
        "-u", "--webhook-url",
        type=str,
        help="Send group results to <url>",
        metavar="<url>")
    parser.add_argument(
        "-c", "--cut-off",
        default=group_id,
        type=parse_human_number,
        help="ID limit for skipping missing groups",
        metavar="<id>")
    parser.add_argument(
        "-C", "--chunk-size",
        default=100, 
        type=int,
        help="Number of groups to be sent per batch request",
        metavar="<num>")
    parser.add_argument(
        "-T", "--timeout",
        default=5.0,
        type=float,
        help="Timeout for connections and responses",
        metavar="<float>")
    args = parser.parse_args()
    return args
