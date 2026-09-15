# Woow Frigate (WOOWTECH mirror)

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FWOOWTECH%2FWoow_ha_frigate_add_on)

WOOWTECH 維護的 **Frigate** 防失聯鏡像。git 內容與容器映像都重新託管在
WOOWTECH 名下，上游若失聯、刪庫或改權限，既有安裝不受影響。

- 上游：[blakeblackshear/frigate-hass-addons](https://github.com/blakeblackshear/frigate-hass-addons)
- 本鏡像 add-on：`frigate` v0.17.2
- 映像：`ghcr.io/blakeblackshear/frigate` → `ghcr.io/woowtech/ha-mirror-*`

## 安裝

點上方按鈕，或 HA UI → **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
貼上：

```
https://github.com/WOOWTECH/Woow_ha_frigate_add_on
```

也可以只加 [WoowTech HA App Store](https://github.com/WOOWTECH/Woow_HA_App_Store)
這一個 URL，本 add-on 已收錄其中。

## 分支

| 分支 | 內容 |
|---|---|
| `main` | 上游 + WOOWTECH overlay，且 `image:` 已改指向 WOOWTECH GHCR。**HA 讀這個分支。** |
| `upstream` | 上游預設分支的完整未修改鏡像（不 prune），供稽核與復原用 |

## 自動化

| Workflow | 排程 (UTC) | 做什麼 |
|---|---|---|
| `mirror-sync` | 03:17 每日 | 拉上游 → 更新 `upstream` 分支 → 依 `KEEP_SUBDIRS` 裁切 → 套 overlay → 改寫 `image:` → force-push `main` |
| `image-mirror` | 04:47 每日 | 讀 `.mirror/image-map.json`，用 skopeo 把上游映像複製到 `ghcr.io/woowtech/ha-mirror-*` |

細節與 `KEEP_SUBDIRS` 的理由見 [`.mirror/README.md`](.mirror/README.md)。

## 授權

Add-on 內容沿用上游授權（見 `frigate LICENSE` 內的 LICENSE）。WOOWTECH 僅新增
`.github/`、`.mirror/`、`repository.yaml` 與本 README。
