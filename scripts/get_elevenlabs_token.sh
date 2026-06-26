#!/bin/bash
# Extract the Firebase bearer token from the ElevenLabs browser session via Playwriter.
# Usage: TOKEN=$(bash scripts/get_elevenlabs_token.sh)
# Requires: Playwriter extension active in Chrome, logged into ElevenLabs.

SESSION="${1:-1}"

playwriter -s "$SESSION" -e '
const t = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.includes("authUser"))
            return JSON.parse(localStorage.getItem(key))?.stsTokenManager?.accessToken;
    }
});
console.log(t);
' 2>/dev/null | grep '\[log\]' | sed 's/\[log\] //' | tr -d "'"
