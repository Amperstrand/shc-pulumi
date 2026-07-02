#!/bin/bash
# Regenerate src/shc_pulumi/sizes.py from the live SHC catalog.
# Run from the shc-pulumi repo root.
#
# Usage:
#   SHC_API_KEY=... ./scripts/regenerate_sizes.sh

set -e

TOOLKIT_GEN="../shc-toolkit/scripts/generate_sizes.py"

if [ -f "$TOOLKIT_GEN" ]; then
    python3 "$TOOLKIT_GEN" --format pulumi --output src/shc_pulumi/sizes.py
else
    pip install git+https://github.com/Amperstrand/shc-toolkit.git -q
    curl -sL https://raw.githubusercontent.com/Amperstrand/shc-toolkit/main/scripts/generate_sizes.py \
        | python3 - --format pulumi --output src/shc_pulumi/sizes.py
fi

echo "Done. Review the diff and commit."
