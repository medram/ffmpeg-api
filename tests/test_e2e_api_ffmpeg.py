# moved from root
def main():
    import runpy
    import sys

    sys.path.insert(0, ".")
    runpy.run_path("../test_e2e_api_ffmpeg.py", run_name="__main__")


if __name__ == "__main__":
    main()
