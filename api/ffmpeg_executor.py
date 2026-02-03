import asyncio
import os
import re
import shlex
import shutil


class FFmpegExecutor:
    """Handles FFmpeg command execution with simple placeholder templating.

    Supported placeholders inside command_args:
    - {{ output_filename }} -> replaced with shell-quoted output path
    - {{ in_N }} (e.g. {{ in_1 }}) -> replaced with Nth input file path (1-based)
    - {{ <input_key> }} -> if input_key matches a key in input_files, replaced with that path

    If no output placeholder is present, the output_path will be appended to the command.
    """

    @staticmethod
    def check_ffmpeg_installed() -> bool:
        """Check if FFmpeg is installed on the system."""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    async def execute(
        command_args: str,
        input_files: dict[str, str],
        output_path: str | None = None,
        output_files: dict[str, str] | None = None,
    ) -> tuple[bool, str | None]:
        """Execute an FFmpeg command.

        Args:
            command_args: FFmpeg command arguments (without 'ffmpeg' prefix)
            input_files: Dict mapping filenames to local file paths
            output_path: Path where output file should be written

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not FFmpegExecutor.check_ffmpeg_installed():
            return False, "FFmpeg is not installed on the system"

        # Work on a copy
        command_str = command_args

        # Prepare ordered list of input paths for in_1, in_2, ...
        # Ensure all are absolute paths (defensive, but should already be absolute)
        ordered_inputs = [os.path.abspath(p) for p in input_files.values()]

        # Helper to shell-quote paths
        def q(path: str) -> str:
            return shlex.quote(path)

        # Replace {{ ... }} placeholders
        pattern = re.compile(r"{{\s*([^}]+)\s*}}")

        def replace_placeholder(match: re.Match) -> str:
            key = match.group(1)
            # output placeholder: check output_files mapping first
            if key in ("output_filename", "output", "output_path"):
                return q(output_path) if output_path is not None else match.group(0)
            # named output keys (e.g. out_1)
            if output_files and key in output_files:
                return q(output_files[key])
            # in_N placeholder
            m = re.fullmatch(r"in_(\d+)", key)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(ordered_inputs):
                    return q(ordered_inputs[idx])
                return match.group(0)
            # direct input key (match against input_files keys)
            if key in input_files:
                # Always use the absolute path, never join again
                return q(os.path.abspath(input_files[key]))
            # unknown placeholder -> leave unchanged
            return match.group(0)

        command_str = pattern.sub(replace_placeholder, command_str)

        # Remove legacy replacement of non-placeholder input filenames to avoid accidental double paths
        # (No longer needed and can cause double temp dir issues)

        # If command doesn't contain an explicit output placeholder and a single output_path provided,
        # append the output path (legacy behavior). If multiple output_files provided, do not auto-append.
        if (not output_files) and (
            "{{" not in command_args and "output" not in command_str and output_path
        ):
            command_str = f"{command_str} {q(output_path)}"

        # Ensure the command is prefixed with ffmpeg
        full_command = command_str.strip()
        if not full_command.startswith("ffmpeg"):
            full_command = f"ffmpeg {full_command}"

        try:
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else stdout.decode()
                return False, f"FFmpeg error: {error_msg}"

            return True, None

        except Exception as e:
            return False, f"Failed to execute FFmpeg: {str(e)}"
