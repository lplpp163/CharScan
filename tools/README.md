# LeafCarbon 重生工具

資料或企劃書內容更新後，用這兩支腳本把 **demo 數據** 與 **繳件 PDF** 重新生成。

## 一次性安裝（PDF 工具需要）

```bash
cd CharScan/tools
npm install          # 裝 markdown-it + mermaid
```

Python 端需要 `pandas numpy scikit-learn`（本機已備）。

## 1. 重生 demo 數據（demo_data.js）

模型完全比照 `cnn_biomass.py`：側拍結構 `sd_*` + 累積環境 `temp/cum_sun/cum_gdd/cum_uv`、
RandomForest 400 棵、leave-one-day-out 交叉驗證、raw/log 取較佳。信心區間取 400 棵樹的預測分布。

```bash
cd CharScan/tools
python gen_demo_data.py ../../03_實驗數據/results/perplant_features.csv ../demo/demo_data.js
```

> `perplant_features.csv` 是 72 株的特徵表，由遠端 `cnn_biomass.py` 產生、已複製到
> `03_實驗數據/results/`。若資料再更新，從遠端重抓該檔覆蓋即可。
> 會印出 R²/RMSE/n；目前為 R²≈0.64、RMSE≈0.43、72 株、24 天。

## 2. 重生繳件 PDF

把 Markdown 轉成 PDF（自動渲染 mermaid 流程圖、內嵌圖片、用微軟正黑）。

```bash
cd CharScan/tools
node build_pdf.js <輸入.md> <輸出.pdf>
```

四份繳件 + CharScan 副本一次重生：

```bash
cd CharScan/tools
B="../../05_報名繳件_英文"
for f in 01_Summary_Table_of_Project_Descriptions 01_作品介紹摘要表_中文閱讀版 \
         02_LeafCarbon_Project_Plan_EN 02_LeafCarbon_Project_Plan_中文閱讀版; do
  node build_pdf.js "$B/$f.md" "$B/$f.pdf"
done
cp "$B/02_LeafCarbon_Project_Plan_中文閱讀版.pdf" ../docs/LeafCarbon_企劃書_中文版.pdf
cp "$B/01_Summary_Table_of_Project_Descriptions.pdf" ../docs/Summary_Table_EN.pdf
cp "$B/01_作品介紹摘要表_中文閱讀版.pdf" ../docs/摘要表_中文閱讀版.pdf
```

英文為主源；中文閱讀版改完內容後一起重生 PDF。
