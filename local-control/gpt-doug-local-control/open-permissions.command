#!/bin/bash
# macOS does not permit apps/scripts to silently grant TCC permissions.
# This opens Privacy & Security so the user can approve the terminal/app running this agent.
open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" || open "x-apple.systempreferences:com.apple.preference.security"
