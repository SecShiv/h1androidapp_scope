#!/bin/sh
python3 h1androidapp.py

echo "# h1domains\nhackerone \"in-scope\" domains\n\n\`python3 h1androidapp.py\`" > README.md
echo "## Android Apps with Bounties (Last Updated `date`)" >> README.md
echo "\`\`\`" >> README.md
echo "`cat android_apps_with_bounties.txt`" >> README.md
echo "\`\`\`" >> README.md
