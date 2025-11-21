# Backward-compatible shim: prefer importing from `runexperiment`.
if __name__ == "__main__":
    from runexperiment.__main__ import main

    main()
