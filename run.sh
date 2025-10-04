#!/bin/sh
python3 h1androidapp.py

echo "# h1android\nhackerone \"in-scope\" apps\n\n\`python3 h1androidapp.py\`" > README.md
echo "## Android Apps with Bounties (Last Updated `date`)" >> README.md
echo "\`\`\`" >> README.md
echo "`cat android_apps_with_bounties.txt`" >> README.md
echo "\`\`\`" >> README.md

pip3 install waymore --break
waymore -i hackerone.com -mode U -n | grep -oP 'https?://\S+/embedded_submissions/new\S*' | sort -u > hackerone_private.txt
