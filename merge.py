# -*- coding: utf-8 -*-

import copy
import glob
import json

from collections import defaultdict


NTHU_CONTRIBUTOR = "CYR"  # Ying-Ren Chen
NTHU_DATA_PATH = "data/nthu_extension/"
PETGAME_DATA_PATH = "data/petgame/"


def load_petgame_contributor():
    """Load assertions from the pet game raw data.
    
    Returns
    -------
    contributors: dict
        A dictionary of assertion (frame id, concept 1, concept 2) to a list of
        the pet game contributors.
    """
    contributors = defaultdict(list)
    filenames = glob.glob(PETGAME_DATA_PATH + "conceptnet_zh_*.txt")
    for filename in filenames:
        print("Loading {}".format(filename))
        with open(filename) as fp:
            lines = fp.readlines()
            for line in lines:
                fields = line.strip().split(", ")
                if len(fields) < 4:
                    continue
                # frame id, concept1, concept2
                assertion = (fields[1], fields[2], fields[3])
                contributors[assertion].append(fields[0])
    return contributors


def load_frames(json_path):
    """Load the frame data from the json.

    Returns
    -------
    text2frames: dict
        A dictionary that maps frame text to the frame data.
    id2frames: dict
        A dictionary that maps frame id to the frame text.
    """
    text2frames = {}
    id2frames = {}
    with open(json_path) as fp:
        data = json.load(fp)
        for frame_id, frame in data.items():
            id2frames[frame_id] = frame["text"].encode("utf-8").strip()
            frame["id"] = frame_id
            frame["order"] = "12" if frame["text"].index("1") < frame["text"].index("2") else "21"
            frame["text"] = frame["text"].encode("utf-8").strip().replace("{1}", "{}")
            frame["text"] = frame["text"].replace("{2}", "{}").replace("。", "")
            text2frames[frame["text"]] = frame
    return text2frames, id2frames


def parse_surface_text(surface_text, frames):
    """Parse the surface text into frame id, concepts, and relation.

    Parameters
    ----------
    surface_text: str
        The input surface text, with concepts wrapped in ``[[]]''.
    frames: dict
        The dictionary that maps from frame text to data.

    Returns
    -------
    tuple
        A 4-tuple of frame id, concept 1, concept 2, and relation.
    """
    parts = surface_text.replace("。", "").split()
    concepts = []
    for i, part in enumerate(parts):
        if "[[" in part:
            concepts.append(part.replace("[[", "").replace("]]", ""))
            parts[i] = "{}"
        else:
            parts[i] = part
    frame_text = " ".join(parts)
    if frame_text not in frames.keys():  # cannot find the frame
        print("\tCannot find frame: {}".format(frame_text))
        return None
    frame = frames[frame_text]
    assert frame["order"] in ["12", "21"], "Not a valid concept order"
    if frame["order"] == "12":
        return (frame["id"], concepts[0], concepts[1], frame["relation"])
    elif frame["order"] == "21":
        return (frame["id"], concepts[1], concepts[0], frame["relation"])


def find_contributors(frame, frame_mapping, contributors, frames, out_fp, reversed=False):
    """Find the pet game contributor of the parsed sentence and append to the output file.

    Parameters
    ----------
    frame: tuple
        The 4-tuple of the parsed surface text with frame id, concepts, and relation.
    frame_mapping: dict
        A dictionary that maps the new frame id to a list of old frame ids.
    contributors: dict
        A dictionary of the pet game contributors. It maps from an assertion to a list of user names.
    frames: dict
        A dictionary that maps frame id to its text form.
    out_fp
        The output file handle.
    reversed: bool
        Is the concept order reversed or not.

    Returns
    -------
    bool
        Find the pet game contributors or not.
    """
    frame_id, concept1, concept2, rel = frame
    for old_frame_id in frame_mapping[frame_id]:
        frame = (old_frame_id, concept1, concept2)
        if frame in contributors:  # check for the correct order
            if not reversed:
                print("{}, {}, {}, {}: {}".format(rel, frames[frame_id],
                    concept1, concept2, len(contributors[frame])))
                for contributor in contributors[frame]:
                    out_fp.write("{}, {}, {}, {}\n".format(contributor, frame_id, concept1, concept2))
            else:
                print("{}, {}, {}, {}: {}".format(rel, frames[frame_id],
                    concept2, concept1, len(contributors[frame])))
                for contributor in contributors[frame]:
                    out_fp.write("{}, {}, {}, {}\n".format(contributor, frame_id, concept2, concept1))
            return True
    return False


def convert_nthu_data(filename, contributors, out_filepath):
    """Go through the lines of the input csv file, find the contributors and the mapped
    frame id to output to a structured output.

    Parameters
    ----------
    filename: str
        File name of the input csv file. Each line is the surface form of an assertion.
    contributors: dict
        A dictionary of the pet game contributors. It maps from an assertion to a list of user names.
    out_filepath: str
        The output file path. Each line is the frame id and concepts with the contributor's name.
    """

    # Load the frame data
    text2frames, id2frames = load_frames("data/zh_frames_new.json")
    frame_mapping = {}
    with open("data/frames_mapping.json") as fp:
        frame_mapping = json.load(fp)
    filepath = NTHU_DATA_PATH + filename
    # Go through the file to process each surface sentence
    out_fp = open(out_filepath, "a")
    with open(filepath) as fp:
        lines = fp.readlines()
        for line in lines:
            fields = line.strip().split(",")
            if len(fields) < 7:
                continue
            # Identify the mapped frame ID
            _, c1, c2, rel, sent, _, _ = fields
            parsed_frame = parse_surface_text(sent, text2frames)
            if parsed_frame is None:
                continue  # cannot find the frame
            # Find the contributors and output to the text file
            found = find_contributors(parsed_frame, frame_mapping, contributors, id2frames, out_fp)
            if not found:  # the old one may have concept reversed
                reversed_frame = (parsed_frame[0], parsed_frame[2], parsed_frame[1], parsed_frame[3])
                found = find_contributors(reversed_frame, frame_mapping, contributors,
                                          id2frames, out_fp, reversed=True)
            if not found:  # this is a new frame
                print("New assertion: {}, {}, {}, {}".format(parsed_frame[3],
                    id2frames[parsed_frame[0]], parsed_frame[1], parsed_frame[2]))
                out_fp.write("{}, {}, {}, {}\n".format(NTHU_CONTRIBUTOR,
                    parsed_frame[0], parsed_frame[1], parsed_frame[2]))
    out_fp.close()


def main():
    contributors = load_petgame_contributor()
    convert_nthu_data("ConceptNet_modified.csv", contributors, "data/conceptnet_zh_merged.txt")


if __name__ == '__main__':
    main()
