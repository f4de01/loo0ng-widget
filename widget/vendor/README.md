# 随包客户端

入口为 `zebar-3.3.1.js`，来自 Zebar **3.3.1** 的浏览器 ES2022 bundle。
随包的依赖闭包共 6 个文件，只剩 **@tauri-apps/api 2.0.2**；bundle 内还含
**zod 3.24.2**、**glazewm 1.7.0** 与 **@tauri-apps/plugin-dialog 2.0.0**。
Tauri 的 tslib 辅助代码来自其 2.0.2 包。

`manifest.json` 逐文件记录下载 URL、上游原始字节的 SHA-256 和随包字节的
SHA-256。共做四种修改：将模块导入改为同目录相对路径；移除 sourceMappingURL，
避免开发工具另取未随包的映射；删掉上游对 luxon 的那 10 条导入；把 zebar `date`
provider 里唯一用到 luxon 的那一句改写成抛错说明。后两条见下，升级时要原样重做。

**去掉的 luxon**（#16）。esm.sh 的 bundle 把 luxon 3.4.4 的 10 个模块外部化后逐一
导入，其中 9 个导进来一次都没用到，第 10 个（`DateTime`）只被 zebar 的 `date`
provider 用一句。这张卡片不用任何 provider，那 10 个文件却占着随包字节与白名单。
处理：删掉那 10 条导入语句与对应的文件、许可证、manifest 条目，`date` provider 里
那一句改成抛错说明，其余上游逻辑一个字节没动；`zebar-3.3.1.js` 的随包 SHA-256
因此与上游那份不同，两份哈希都记在 manifest 里。再要用 `date` provider，就得把
luxon 连同它的依赖闭包一起取回来。`tests/test_package.py` 守着这几条。

上游保留了 `import("ws")`，仅在不存在浏览器原生 WebSocket 的 Node 环境才执行；
本包只运行于 Zebar WebView，不支持 Node，也不安装该 Node 依赖。客户端与宿主的
本机 IPC／localhost 通信仍然保留，不属于外部网络请求。

## 来源与许可证

第三方代码不适用仓库根目录的 MIT 声明；原始许可证随包放在 `licenses/`。

- Zebar 3.3.1：GPL-3.0-only；[对应源码下载（含构建配置和锁文件）](https://github.com/glzr-io/zebar/archive/refs/tags/v3.3.1.tar.gz)。
- Tauri API 2.0.2、plugin-dialog 2.0.0：MIT OR Apache-2.0；
  [源码](https://github.com/tauri-apps/tauri)、[插件源码](https://github.com/tauri-apps/plugins-workspace)。
- zod 3.24.2、glazewm 1.7.0：MIT；各包许可证含原作者声明。
- tslib：Microsoft 的 BSD-0-Clause 辅助代码，保留其版权与许可证。

## 有意升级

不在安装或运行时下载代码。升级需同时修改入口版本、重新取得完整浏览器依赖闭包、
更新 manifest 的来源与两组哈希、核对许可证，然后审查所有导入均落在包内；
上面那 10 条导入在新版本里会回来，要照样去掉并重记随包哈希。
保持 `zpack.json` 的 `vendor/**` 白名单覆盖全部资源。
升级后必须重做无缓存的断网宿主启动、运行期外部请求观察，以及 Python 3.9 全套验证。
不能只把 URL 中的版本换掉，也不能依赖 esm.sh 的 `?bundle` 自动包含依赖。
