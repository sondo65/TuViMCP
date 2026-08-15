#!/bin/bash
# Fetch Noto Serif CJK SubsetOTF Regular+Bold for SC/JP/KR from notofonts/noto-cjk
# Creates exactly: NotoSerifSC-Regular.otf, NotoSerifSC-Bold.otf, NotoSerifJP-Regular.otf, 
#                  NotoSerifJP-Bold.otf, NotoSerifKR-Regular.otf, NotoSerifKR-Bold.otf
# Output directory: tuvi_mcp/_fonts/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FONTS_DIR="${PROJECT_ROOT}/tuvi_mcp/_fonts"

# notofonts/noto-cjk raw SubsetOTF folder URL 
BASE_URL="https://github.com/notofonts/noto-cjk/raw/main/Serif/SubsetOTF"

# Font files with their download info (filename:region)
FONTS=(
    "NotoSerifSC-Regular.otf:SC"
    "NotoSerifSC-Bold.otf:SC"
    "NotoSerifJP-Regular.otf:JP" 
    "NotoSerifJP-Bold.otf:JP"
    "NotoSerifKR-Regular.otf:KR"
    "NotoSerifKR-Bold.otf:KR"
)

echo "Downloading Noto Serif CJK SubsetOTF fonts to ${FONTS_DIR}/"

# Ensure fonts directory exists
mkdir -p "${FONTS_DIR}"

# Download each font file
for font_info in "${FONTS[@]}"; do
    IFS=':' read -r font_file region <<< "${font_info}"
    url="${BASE_URL}/${region}/${font_file}"
    output_path="${FONTS_DIR}/${font_file}"
    
    if [[ -f "${output_path}" ]]; then
        # Check if existing file is valid (not HTML)
        if file "${output_path}" | grep -q "HTML\|text"; then
            echo "  ${font_file} exists but is invalid (HTML), re-downloading"
            rm -f "${output_path}"
        else
            echo "  ${font_file} already exists, skipping"
            continue
        fi
    fi
    
    echo "  Downloading ${font_file} from ${region}..."
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "${output_path}" "${url}"
    elif command -v wget >/dev/null 2>&1; then
        wget -O "${output_path}" "${url}"
    else
        echo "Error: Neither curl nor wget found. Cannot download fonts."
        exit 1
    fi
    
    # Verify file was downloaded and is a valid font file
    if [[ -f "${output_path}" ]]; then
        size=$(stat -f%z "${output_path}" 2>/dev/null || stat -c%s "${output_path}" 2>/dev/null || wc -c < "${output_path}")
        filetype=$(file "${output_path}")
        
        if [[ $size -gt 100000 ]] && ! echo "${filetype}" | grep -q "HTML\|text"; then
            echo "  ✓ ${font_file} downloaded successfully (${size} bytes)"
        else
            echo "  ✗ ${font_file} download failed - size: ${size}, type: ${filetype}"
            rm -f "${output_path}"
            exit 1
        fi
    else
        echo "  ✗ ${font_file} download failed - file not created"
        exit 1
    fi
done

echo "CJK font download complete. Verifying files..."

# Final verification
for font_info in "${FONTS[@]}"; do
    IFS=':' read -r font_file region <<< "${font_info}"
    output_path="${FONTS_DIR}/${font_file}"
    if [[ -f "${output_path}" ]]; then
        size=$(stat -f%z "${output_path}" 2>/dev/null || stat -c%s "${output_path}" 2>/dev/null || wc -c < "${output_path}")
        echo "  ${font_file}: ${size} bytes"
    else
        echo "  ${font_file}: MISSING"
    fi
done

echo "All CJK fonts ready for packaging."