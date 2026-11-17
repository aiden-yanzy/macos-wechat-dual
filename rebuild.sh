#!/bin/bash
# 微信双开重建脚本（macOS 26 / 微信 4.x 实测通过）
# 微信升级后执行一次即可把第二副本刷新到最新版；主微信不受影响。
#
# 用法:
#   ./rebuild.sh                     # 默认：/Applications/WeChat.app -> /Applications/WeChat2.app
#   SRC=/path/WeChat.app DST=/Applications/WeChat3.app ./rebuild.sh
set -euo pipefail

SRC="${SRC:-/Applications/WeChat.app}"
DST="${DST:-/Applications/WeChat2.app}"
NEWID="${NEWID:-com.tencent.xinWeChat2}"
DISPLAY_NAME="${DISPLAY_NAME:-微信 2}"
WORK="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[ -d "$SRC" ] || { echo "找不到 $SRC"; exit 1; }
[ "$SRC" != "$DST" ] || { echo "SRC 与 DST 不能相同"; exit 1; }

echo "== 1. 关闭旧副本进程 =="
pkill -f "$DST/Contents/MacOS/WeChat\$" 2>/dev/null || true
sleep 1

echo "== 2. 复制原版微信 =="
rm -rf "$DST"
ditto "$SRC" "$DST"

echo "== 3. 生成带「2」徽章的图标 =="
sips -s format png "$DST/Contents/Resources/AppIcon.icns" --out "$TMP/base.png" >/dev/null
/usr/bin/python3 "$WORK/make_icon.py" "$TMP/base.png" "$TMP/icon.iconset"
iconutil -c icns "$TMP/icon.iconset" -o "$DST/Contents/Resources/AppIcon2.icns"

echo "== 4. 改写 Info.plist =="
P="$DST/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $NEWID" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleName WeChat 2" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $DISPLAY_NAME" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleGetInfoString $DISPLAY_NAME" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile AppIcon2" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleIconName AppIcon2" "$P"
# 移除 URL scheme，避免与主微信抢 weixin:// 的打开权
/usr/libexec/PlistBuddy -c "Delete :CFBundleURLTypes" "$P" 2>/dev/null || true

echo "== 5. 改写本地化显示名（保留隐私权限文案） =="
/usr/bin/python3 - "$SRC" "$DST" "$DISPLAY_NAME" <<'PY'
import re, sys
src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
en_name = "WeChat 2"
for lproj in ("zh-Hans", "en", "zh-Hant"):
    p_in = f"{src}/Contents/Resources/{lproj}.lproj/InfoPlist.strings"
    p_out = f"{dst}/Contents/Resources/{lproj}.lproj/InfoPlist.strings"
    try:
        text = open(p_in, "rb").read().decode("utf-16")
    except FileNotFoundError:
        continue
    newname = name if lproj == "zh-Hans" else en_name
    text = re.sub(r'("CFBundleDisplayName"\s*=\s*")[^"]*(")', lambda m: m.group(1) + newname + m.group(2), text)
    text = re.sub(r'("CFBundleName"\s*=\s*")[^"]*(")', lambda m: m.group(1) + newname + m.group(2), text)
    open(p_out, "wb").write(text.encode("utf-16"))
PY

echo "== 6. 清除隔离属性 + ad-hoc 重签 =="
xattr -cr "$DST" 2>/dev/null || true
codesign --force --deep --sign - --options runtime \
         --entitlements "$WORK/entitlements.plist" "$DST"
codesign --verify --deep --strict "$DST"

echo "== 7. 刷新 LaunchServices =="
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$DST"

echo "== 8. 启动 =="
open -n -a "$DST"
sleep 4
pgrep -f "$DST/Contents/MacOS/WeChat\$" >/dev/null \
    && echo "OK：$DISPLAY_NAME 已启动（登录窗口应已弹出）" \
    || echo "失败：请查看 ~/Library/Logs/DiagnosticReports/"
