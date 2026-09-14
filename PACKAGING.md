# 打包与运行说明

本文档说明如何把 MarkiNote 打包成 Windows 桌面软件，以及打包后应用的行为。

## 一、开发环境运行

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
python main.py
```

启动后会自动打开界面。数据目录与项目目录**分离**，见下文。

## 二、运行时环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MARKINOTE_HOST` | `127.0.0.1` | 监听地址。改成 `0.0.0.0` 才会被局域网访问，此时**没有任何鉴权**，请自行评估 |
| `MARKINOTE_PORT` | `5000` | 首选端口；被占用时自动改用空闲端口 |
| `MARKINOTE_DEBUG` | 关闭 | 设为 `1` 开启 Flask 调试模式。**不要对外使用**，调试器暴露等于可远程执行代码 |
| `MARKINOTE_WINDOW` | 开启 | 设为 `0` 则不使用原生窗口，改用系统浏览器 |
| `MARKINOTE_NO_BROWSER` | 关闭 | 设为 `1` 则不自动打开界面（服务器/自动化场景用） |

## 三、用户数据目录

用户的 Markdown 笔记**不在项目目录里**，而是存放在系统标准的用户数据目录：

| 系统 | 路径 |
|---|---|
| Windows | `%APPDATA%\MarkiNote\lib` |
| macOS | `~/Library/Application Support/MarkiNote/lib` |
| Linux | `$XDG_DATA_HOME/MarkiNote/lib` |

这么设计的原因：打包成 exe 后，程序所在目录可能是临时解压目录或只读的安装目录，
把笔记存在那里会丢失或写不进去。

仓库里的 `lib/` 是**种子模板**：首次运行且数据目录为空时，其中的文件会被复制进数据目录，
这样新用户第一次打开看到的是新手指南而不是空目录。之后不再覆盖。

## 四、打包成 exe

```bash
.venv\Scripts\pip install pyinstaller pywebview
.venv\Scripts\pyinstaller MarkiNote.spec --noconfirm --clean
```

产物在 `dist\MarkiNote\`，双击 `MarkiNote.exe` 即可运行。

采用 **onedir** 而非 onefile：onefile 每次启动都要把全部内容解压到临时目录，
冷启动慢数倍，而且自解压行为是杀毒软件误报的主要来源。

新增依赖的注意事项：如果以后引入新的第三方库，并且像 pywebview 那样**动态加载**子模块，
需要把对应模块加进 `MarkiNote.spec` 的 `hiddenimports`，否则打包后运行时报 ImportError。

## 五、制作安装包

前置：安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)，并先完成上一步的打包。

```bash
iscc installer\MarkiNote.iss
```

产物：`installer\Output\MarkiNote-<版本>-setup.exe`（约 22 MB，含开始菜单项、
桌面快捷方式、卸载程序）。版本号在 `installer\MarkiNote.iss` 顶部的 `AppVersion` 处修改。

**中文语言包**：Inno Setup 官方安装包不自带简体中文（属于非官方翻译），
因此 `installer\ChineseSimplified.isl` 随项目一起提交，克隆仓库后可直接编译。

**静默安装**（批量部署用）：

```
MarkiNote-1.0.0-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="目标路径"
```

注意：如果 MarkiNote 正在运行，Inno Setup 会先尝试关闭它。交互模式下会弹窗提示，
静默模式下会直接中止安装（这是 Inno Setup 的默认防冲突行为，故意不改成强制结束进程——
本程序有编辑器，强杀可能丢失未保存的修改）。

卸载时只删除程序本体，**不会删除** `%APPDATA%\MarkiNote` 下的用户笔记。

## 六、文件关联

安装包会把本程序加进 `.md` / `.markdown` 的**「打开方式」候选**（安装时勾选该任务）。

不去抢默认关联有两个原因：Windows 10+ 会阻止程序私自修改默认关联（用户必须在
「设置」里自己确认），而且抢默认本身也不是礼貌的行为。右键文件 →「打开方式」→
MarkiNote 即可。

程序侧是真的支持：`main.py` 的 `document_from_argv()` 会从命令行里取出文档路径，
在库内的直接打开，在库外的复制进库根目录再打开。所以关联不是"双击能启动但不打开
那个文件"的假承诺。

## 七、尚未实现

- **自动更新**：需要托管版本清单并处理签名，当前需手动下载新版本安装包覆盖。
- **代码签名**：未签名的 exe 在 Windows SmartScreen 下会提示"未知发布者"，
  用户需点"仍要运行"。正式分发建议购买代码签名证书。
- **拖拽导入文件夹**：目前只处理拖进来的文件；拖文件夹需要 `webkitGetAsEntry`
  递归展开，尚未实现。
