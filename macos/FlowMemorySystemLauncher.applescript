on run
    set appBundlePath to POSIX path of (path to me)
    set projectRoot to do shell script "cd " & quoted form of (appBundlePath & "..") & " && /bin/pwd"
    set pythonBin to projectRoot & "/.venv/bin/python"
    set appScript to projectRoot & "/fm_app.py"
    set requirementsFile to projectRoot & "/requirements.txt"

    set appMissing to do shell script "/bin/test -f " & quoted form of appScript & " && printf no || printf yes"
    if appMissing is "yes" then
        display dialog "Could not find fm_app.py next to the app bundle.\n\nExpected project root:\n" & projectRoot & "\n\nPlease keep Flow Memory System.app inside the project folder." buttons {"OK"} default button "OK" with title "Flow Memory System"
        return
    end if

    set pythonMissing to do shell script "/bin/test -x " & quoted form of pythonBin & " && printf no || printf yes"
    if pythonMissing is "yes" then
        display dialog "Missing Python virtual environment.\n\nExpected:\n" & pythonBin & "\n\nCreate it with:\n/opt/homebrew/bin/python3.13 -m venv \"" & projectRoot & "/.venv\"\n\"" & projectRoot & "/.venv/bin/python\" -m pip install -r \"" & requirementsFile & "\"" buttons {"OK"} default button "OK" with title "Flow Memory System"
        return
    end if

    do shell script "cd " & quoted form of projectRoot & " && /usr/bin/nohup " & quoted form of pythonBin & " " & quoted form of appScript & " >/tmp/flow-memory-system.log 2>&1 &"
end run
