# macos-wechat-dual

在 macOS 上双开微信：复制一份 WeChat.app、换成独立 Bundle ID、换上带「2」角标的图标、ad-hoc 重签，两个微信进程/数据/图标完全独立，可同时在线。

适用于 **微信 4.x（macOS 26 实测 4.1.15）**。

## 效果

| 项目 | 原版 | 副本 |
|---|---|---|
| 路径 | `/Applications/WeChat.app` | `/Applications/WeChat2.app` |
| Bundle ID | `com.tencent.xinWeChat` | `com.tencent.xinWeChat2` |
| 显示名 | 微信 | 微信 2 |
| 图标 | 微信绿 | 微信绿 + 右下橙色「2」徽章 |
| 沙盒容器 | `~/Library/Containers/com.tencent.xinWeChat` | `~/Library/Containers/com.tencent.xinWeChat2` |
| 签名 | Tencent 官方签名 | ad-hoc 重签 |

两个实例的进程、容器、偏好域、mach 端口、单实例锁全部独立，互不干扰。

## 快速开始

```bash
git clone https://github.com/aiden-yanzy/macos-wechat-dual.git
cd macos-wechat-dual
chmod +x rebuild.sh
./rebuild.sh
```

脚本会：复制原版微信 → 生成角标图标 → 改 Bundle ID/显示名 → 保留隐私权限文案 → ad-hoc 重签 → 刷新 LaunchServices → 启动并弹出扫码窗。

需要 Pillow：

```bash
/usr/bin/python3 -m pip install --user pillow
# 或 brew install python-pillow
```

## 自定义

```bash
# 再开第三份
SRC=/Applications/WeChat.app DST=/Applications/WeChat3.app NEWID=com.tencent.xinWeChat3 ./rebuild.sh

# 换显示名
DISPLAY_NAME="工作微信" ./rebuild.sh
```

只换图标（不动应用）：

```bash
/usr/bin/python3 make_icon.py /Applications/WeChat.app/Contents/Resources/AppIcon.icns ./icon.iconset
iconutil -c icns ./icon.iconset -o AppIcon2.icns
```

## 微信升级后

主微信自动更新只替换 `/Applications/WeChat.app`，副本不会跟着变。要同步到最新版，重跑一次 `./rebuild.sh` 即可；副本的登录数据在自己的容器里，重建应用不会丢登录态。

## 原理与踩过的坑

1. **必须换 Bundle ID**。macOS 上沙盒容器路径、偏好域、mach 服务名（`…MachPortRendezvousServer`）、单实例锁都由 Bundle ID 派生。只 `cp` 一份的所谓「双开」会共用同一个容器，启动即互相抢数据——这就是绝大多数失败双开的原因。

2. **不能保留 app-sandbox**。微信 4.x 带 `com.apple.security.app-sandbox`，组容器要求签名里有 Team ID 前缀。ad-hoc 签名没有 Team ID，`containermanagerd` 会直接拒绝：

   ```
   Group containers identifiers should be prefixed by requestor's team ID
   ```

   同时 `mach-register` 也被 sandbox 拒绝。所以副本需剥离沙盒，以非沙盒方式运行，数据落在按 Bundle ID 命名的目录里。

3. **必须重签**。改了 `Info.plist` 与资源，原签名立即失效，需 `codesign --force --deep --sign -`。同时用 `--entitlements` 保留 `cs.allow-jit`、网络、摄像头等必要权限。

4. **显示名被本地化文件覆盖**。`Contents/Resources/*.lproj/InfoPlist.strings` 是 **UTF-16** 编码，里面除了 `CFBundleDisplayName` 还有麦克风、摄像头、定位、相册、本地网络等授权说明。只能改显示名两行，整文件覆写会丢权限文案。`plutil -replace` 不支持这种 OpenStep 格式，脚本用 Python 读写。

5. **移除 `CFBundleURLTypes`**，否则副本会和主微信抢 `weixin://` 的打开权。

6. **图标缓存**。改完要 `lsregister -f` 刷新，否则 Dock 仍显示旧图标。

## 文件

| 文件 | 说明 |
|---|---|
| `rebuild.sh` | 一键重建/升级，支持 `SRC`/`DST`/`NEWID`/`DISPLAY_NAME` 环境变量 |
| `make_icon.py` | 角标图标生成器：橙色渐变 + 白色数字 2 + 白描边 + 投影 |
| `entitlements.plist` | 副本使用的非沙盒 entitlements |
| `AppIcon2.icns` | 预生成好的角标图标 |
| `icon-compare.png` | 原版 / 副本图标对比 |

## 卸载

```bash
pkill -f "WeChat2.app/Contents/MacOS/WeChat$"
rm -rf /Applications/WeChat2.app
rm -rf ~/Library/Containers/com.tencent.xinWeChat2
rm -rf ~/Documents/app_data          # 副本的非沙盒运行残留（若存在）
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain user
```

## 免责

仅供本机多账号登录使用。修改过的副本不再享有腾讯官方签名与公证；微信大版本更新后若启动异常，重跑 `rebuild.sh` 通常是首选解法。
