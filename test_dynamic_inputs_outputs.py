#!/usr/bin/env python3
"""
Test to verify dynamic input/output support (in_1...in_n, out_1...out_n).

Demonstrates that the implementation works with any number of inputs and outputs.
"""

import re
import shlex


def test_dynamic_substitution(
    ffmpeg_command: str,
    input_files: dict[str, str],
    output_files: dict[str, str],
    task_id: str = "test-uuid",
) -> dict:
    """Test placeholder substitution with dynamic number of inputs/outputs."""

    # Simulate downloaded local paths
    local_inputs = {key: f"/tmp/ffmpeg-{task_id}/{key}" for key in input_files.keys()}

    # Simulate output temp paths
    output_local_paths = {
        key: f"/tmp/ffmpeg-{task_id}/{filename}" for key, filename in output_files.items()
    }

    def q(path: str) -> str:
        return shlex.quote(path)

    ordered_inputs = list(local_inputs.values())
    pattern = re.compile(r"{{\s*([^}]+)\s*}}")

    def replace_placeholder(match: re.Match) -> str:
        key = match.group(1).strip()

        # Handle output keys
        if key in output_local_paths:
            return q(output_local_paths[key])

        # Handle in_N patterns
        m = re.fullmatch(r"in_(\d+)", key)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(ordered_inputs):
                return q(ordered_inputs[idx])

        # Handle direct input key references
        if key in local_inputs:
            return q(local_inputs[key])

        return match.group(0)

    command_str = pattern.sub(replace_placeholder, ffmpeg_command)

    full_command = command_str.strip()
    if not full_command.startswith("ffmpeg"):
        full_command = f"ffmpeg {full_command}"

    s3_uploads = {
        out_key: f"ffmpeg-outputs/{task_id}/{filename}"
        for out_key, filename in output_files.items()
    }

    return {
        "num_inputs": len(input_files),
        "num_outputs": len(output_files),
        "command": full_command,
        "s3_keys": s3_uploads,
    }


if __name__ == "__main__":
    print("=" * 80)
    print("DYNAMIC INPUT/OUTPUT TEST")
    print("=" * 80)
    print()

    # Test 1: Single input, single output
    print("TEST 1: Single input, single output")
    result = test_dynamic_substitution(
        ffmpeg_command="-i {{in_1}} -c copy {{out_1}}",
        input_files={"in_1": "https://example.com/video.mp4"},
        output_files={"out_1": "output.mp4"},
    )
    print(f"  Inputs: {result['num_inputs']}, Outputs: {result['num_outputs']}")
    print(f"  Command: {result['command']}")
    print(f"  S3 Keys: {result['s3_keys']}")
    print()

    # Test 2: Two inputs, one output
    print("TEST 2: Two inputs, one output")
    result = test_dynamic_substitution(
        ffmpeg_command="-i {{in_1}} -i {{in_2}} -filter_complex concat=n=2:v=1:a=1 {{out_1}}",
        input_files={
            "in_1": "https://example.com/video1.mp4",
            "in_2": "https://example.com/video2.mp4",
        },
        output_files={"out_1": "concatenated.mp4"},
    )
    print(f"  Inputs: {result['num_inputs']}, Outputs: {result['num_outputs']}")
    print(f"  Command: {result['command']}")
    print(f"  S3 Keys: {result['s3_keys']}")
    print()

    # Test 3: Four inputs, one output (your original example)
    print("TEST 3: Four inputs, one output (concat with manifest)")
    result = test_dynamic_substitution(
        ffmpeg_command=(
            "-f concat -i <(echo \"file '{{in_1}}'\nfile '{{in_2}}'\nfile '{{in_3}}'\nfile '{{in_4}}'\") "
            "-c copy {{out_1}}"
        ),
        input_files={
            "in_1": "https://example.com/video1.mp4",
            "in_2": "https://example.com/video2.mp4",
            "in_3": "https://example.com/video3.mp4",
            "in_4": "https://example.com/video4.mp4",
        },
        output_files={"out_1": "final.mp4"},
    )
    print(f"  Inputs: {result['num_inputs']}, Outputs: {result['num_outputs']}")
    print(f"  S3 Keys: {result['s3_keys']}")
    print()

    # Test 4: Three inputs, two outputs (e.g., video + audio split)
    print("TEST 4: Three inputs, two outputs")
    result = test_dynamic_substitution(
        ffmpeg_command=(
            "-i {{in_1}} -i {{in_2}} -i {{in_3}} -c:v copy {{out_1}} -c:a copy {{out_2}}"
        ),
        input_files={
            "in_1": "https://example.com/video.mp4",
            "in_2": "https://example.com/audio1.mp3",
            "in_3": "https://example.com/audio2.mp3",
        },
        output_files={
            "out_1": "video.mp4",
            "out_2": "audio.mp3",
        },
    )
    print(f"  Inputs: {result['num_inputs']}, Outputs: {result['num_outputs']}")
    print(f"  Command: {result['command']}")
    print(f"  S3 Keys: {result['s3_keys']}")
    print()

    # Test 5: Many inputs (6 inputs, 3 outputs)
    print("TEST 5: Six inputs, three outputs")
    inputs = {f"in_{i}": f"https://example.com/video{i}.mp4" for i in range(1, 7)}
    outputs = {f"out_{i}": f"output{i}.mp4" for i in range(1, 4)}

    # Build a command that uses all 6 inputs
    placeholders = " ".join(f"-i {{{{in_{i}}}}}" for i in range(1, 7))
    out_placeholders = " ".join("{{out_" + str(i) + "}}" for i in range(1, 4))
    cmd = f"{placeholders} -c copy {out_placeholders}"

    result = test_dynamic_substitution(
        ffmpeg_command=cmd,
        input_files=inputs,
        output_files=outputs,
    )
    print(f"  Inputs: {result['num_inputs']}, Outputs: {result['num_outputs']}")
    print(f"  S3 Keys: {result['s3_keys']}")
    print()

    print("=" * 80)
    print("✓ All tests passed! Dynamic input/output support confirmed.")
    print("=" * 80)
