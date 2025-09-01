# pdf_diff_checker_web

# pdf_diff_checker_web.py

import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import datetime
from io import BytesIO

# ========== 座標抽出 ==========
def extract_coordinates_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc[0]
    words = page.get_text("words")

    data = []
    for w in words:
        x0, y0, x1, y1, text, *_ = w
        text = text.strip()
        if text:
            data.append({
                "text": text,
                "x0": round(x0, 1),
                "y0": round(y0, 1),
                "x1": round(x1, 1),
                "y1": round(y1, 1)
            })
    return pd.DataFrame(data)

def get_text_in_rect(doc, rect):
    return doc[0].get_textbox(fitz.Rect(*rect)).strip()

def draw_highlight(page, rect, is_match):
    color = (0.7, 0.85, 1) if is_match else (1, 0.7, 0.7)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(*rect))
    shape.finish(fill=color, color=None, width=0, fill_opacity=0.5)
    shape.commit()

def compare_with_highlight(coords_df, pdf_a_bytes, pdf_b_bytes):
    doc_a = fitz.open(stream=pdf_a_bytes, filetype="pdf")
    doc_b = fitz.open(stream=pdf_b_bytes, filetype="pdf")
    page_b = doc_b[0]

    differences = []
    for _, row in coords_df.iterrows():
        rect = (row["x0"], row["y0"], row["x1"], row["y1"])
        text_a = get_text_in_rect(doc_a, rect)
        text_b = get_text_in_rect(doc_b, rect)
        is_match = text_a == text_b
        draw_highlight(page_b, rect, is_match)
        if not is_match:
            differences.append((rect, text_a, text_b))

    # 出力バイトストリーム
    pdf_bytes = BytesIO()
    doc_b.save(pdf_bytes)
    pdf_bytes.seek(0)

    # ログ
    log_str = f"差分チェックログ ({datetime.datetime.now()})\n"
    log_str += f"{len(differences)} 箇所の差分が見つかりました。\n\n"
    for i, (rect, a, b) in enumerate(differences, 1):
        log_str += f"{i:02}: {rect} | 元='{a}' → 比較='{b}'\n"
    return differences, pdf_bytes, log_str


# ========== Streamlit UI ==========
st.title("📄 PDF差分チェックツール (Streamlit版)")

pdf_a = st.file_uploader("① 旧PDFをアップロード", type=["pdf"])
pdf_b = st.file_uploader("② 新PDFをアップロード", type=["pdf"])
mode = st.radio("③ 座標モデルを選択", ["旧PDF基準", "新PDF基準", "ハイブリッド"])

if st.button("④ 差分チェックを実行"):
    if not pdf_a or not pdf_b:
        st.warning("旧PDFと新PDFの両方をアップロードしてください。")
    else:
        # アップロードファイルをバイナリで取得
        pdf_a_bytes = pdf_a.getvalue()
        pdf_b_bytes = pdf_b.getvalue()

        if mode == "旧PDF基準":
            coords_df = extract_coordinates_from_pdf(pdf_a_bytes)
        elif mode == "新PDF基準":
            coords_df = extract_coordinates_from_pdf(pdf_b_bytes)
        else:
            coords_old = extract_coordinates_from_pdf(pdf_a_bytes)
            coords_new = extract_coordinates_from_pdf(pdf_b_bytes)
            coords_df = pd.concat([coords_old, coords_new]).drop_duplicates(
                subset=["x0", "y0", "x1", "y1"]).reset_index(drop=True)

        differences, pdf_result, log_str = compare_with_highlight(coords_df,
                                                                 pdf_a_bytes,
                                                                 pdf_b_bytes)

        st.success(f"処理が完了しました！ 差分数：{len(differences)}")

        st.download_button("📥 差分入りPDFをダウンロード",
                           data=pdf_result,
                           file_name="pdf_diff_result.pdf",
                           mime="application/pdf")

        st.download_button("📥 ログをダウンロード",
                           data=log_str,
                           file_name="pdf_diff_log.txt",
                           mime="text/plain")


# ========== 那須技術課用ボタン ==========
if st.button("那須技術課用"):
    st.markdown(
        '[📂 ネットワークフォルダを開く](file://150.1.12.25/pdf)',
        unsafe_allow_html=True
    )
    st.info("LAN内からアクセスできる場合のみ有効です。")
