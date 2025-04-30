
# Code Act Fallback & SSE 進捗バー — 詳細設計  
*2025-04-29 Draft v0.9*

---

## 1. LangGraph 拡張フロー

```mermaid
flowchart TD
    A[interpret_node] --> B[fetch_node]
    B --> C{convert_node<br/>or viz_node}
    C -->|success| F[finish]
    C -- error --> D[fallback_node<br/>(Code Act)]
    D --> F
```

| ノード          | 役割 |
|------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `fallback_node`  | LangGraph ノードで未対応例外を捕捉し、Claude 3 Sonnet (Code Act) に Python コード生成を依頼。生成コードをサンドボックス実行しファイルを返す。 |

---

## 2. フォールバック判定

| レイヤー         | 捕捉する例外 / 条件                                  | fallback_node に転送 |
|------------------|-------------------------------------------------------|------------------------|
| `convert_node`   | `UnsupportedFormatError(fmt)`                         | ✅                     |
| `viz_node`       | `UnsupportedVizParamError(param)`                    | ✅                     |
| 共通             | `ValueError`, `KeyError`, `NotImplementedError`      | ✅                     |
| `fetch_node`     | S3 エラーは 3 回リトライ後に転送                     | ✅                     |
| LLM 呼び出し     | Claude API error                                     | ❌（直接 raise）       |

---

## 3. SSE (Server-Sent Events) 仕様

| event     | data 例 (JSON)                                | 用途                     |
|-----------|------------------------------------------------|--------------------------|
| `stage`   | `{"step":"fetch","status":"start"}`            | プログレスバー更新       |
| `log`     | `{"msg":"S3 prefix = 441/… 12 files"}`         | コンソールへ逐次表示     |
| `code_gen`| `<コード全文>`                                 | Code Act 時のみ          |
| `code_exec`| `{"stdout":"rows=12000","stderr":""}`         | 実行中ログ               |
| `error`   | `{"step":"viz","message":"KeyError: AIRTMP"}` | 赤帯＋処理終了           |

**フロント表示方針**  
- SSE ログは待機中のみ表示し、最終チャット応答には含めない。  
- 段階は `interpret → fetch → convert／viz → finish` の 5 step。

---

## 4. Code Act サンドボックス

| 制限         | 値                          | 実装 API            |
|--------------|-----------------------------|----------------------|
| CPU 時間     | 120 秒                      | `resource.RLIMIT_CPU` |
| メモリ       | 512 MB                      | `resource.RLIMIT_AS`  |
| ファイルサイズ| 10 MB                       | `resource.RLIMIT_FSIZE` |
| 書込パス     | `/tmp/codeact/<uuid>` のみ  | パス検査             |
| 禁止 import  | `subprocess`, `socket`, `os.system` … | AST 解析＋import フィルタ |

---

## 5. Claude 3 Sonnet プロンプト (Code Act)

**System:**  
> You are CodeAct. Generate Python 3.11 code **only**.

**User:**  
> Convert the DataFrame `df` into Parquet and save it under  
> `/tmp/codeact/{{uuid}}/output.parquet`.  
>  
> Return code **only**, no explanation.

---

## 6. 追加依存パッケージ

| ライブラリ             | 用途                         |
|------------------------|------------------------------|
| `seaborn`              | 高度な可視化 (Code Act)       |
| `sse-starlette`        | FastAPI の SSE                |
| `langgraph-codeact`    | LangGraph Code Act 実行       |

---

## 7. API エンドポイント

| メソッド | パス & 説明                        |
|----------|-------------------------------------|
| POST     | `/agent/run` — タスク起動           |
| GET      | `/agent/sse?task_id=<uuid>` — SSE ストリーム |

---

## 8. TODO & マイルストーン

| #   | 作業項目                    | 担当     |
|-----|-----------------------------|----------|
| 1   | `fallback_node.py` 実装    | backend  |
| 2   | `codeact_sandbox.py`       | backend  |
| 3   | `sse.py` エンドポイント    | backend  |
| 4   | `flow.py` ノード追記       | backend  |
| 5   | `Progress.tsx`＋SSE Hook   | frontend |
| 6   | `pytest` 追加              | test     |
| 7   | GitHub Actions に新 tests 追加 | ci  |

---

## Code Act について

公式 `langgraph-codeact` を使用します。  

Poetry で以下を実行してください。

```bash
poetry add langgraph-codeact seaborn sse-starlette
```

---

## 注意

**Code Act ＝ `langgraph-codeact`** です。  
ご指定の記事と同じ、`pip install langgraph-codeact` で入るパッケージを採用します。
