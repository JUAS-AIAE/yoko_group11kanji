# -*- coding: utf-8 -*-
"""
ナレッジ化プロジェクト 紹介動画 生成スクリプト
PIL(Pillow) + imageio_ffmpeg で、Step1/2/3 のスライド解説動画(MP4)を生成する。

- 出力: videos/step1.mp4, step2.mp4, step3.mp4
- 読み上げ音声は付けない(スライド・字幕のみ)。テキストは画像として焼き込む。
各スライドは軽い「ズーム・フェード」風の区切りを付けて、動画らしく見せる。
"""
import os
from PIL import Image, ImageDraw, ImageFont

# ---- 設定 ----
W, H = 1280, 720
FPS = 30
FONT_PATH = r"C:/Windows/Fonts/YuGothM.ttc"
FONT_PATH_BOLD = r"C:/Windows/Fonts/meiryo.ttc"
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
os.makedirs(OUTDIR, exist_ok=True)
SLIDE_SEC = 3.0          # 1スライドの静止時間(秒)
FADE_SEC = 0.6           # スライド間フェード(秒)

BG_TOP = (23, 42, 61)
BG_BOT = (32, 68, 88)
ACCENT = (123, 200, 168)   # 緑系アクセント
ACCENT2 = (255, 205, 110)  # 黄系アクセント
TEXT = (245, 249, 250)
MUTED = (168, 189, 198)

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradient_bg(size, top, bottom):
    img = Image.new("RGB", size, top)
    d = ImageDraw.Draw(img)
    w, h = size
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(top, bottom, y / h))
    return img

def font(size, bold=False):
    return ImageFont.truetype(FONT_PATH_BOLD if bold else FONT_PATH, size)

def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if cur and draw.textlength(cur + ch, font=fnt) > max_w:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
    return lines

def draw_center_text(draw, lines, y, fnt, fill, max_w):
    for ln in lines:
        wln = draw.textlength(ln, font=fnt)
        draw.text(((W - wln) / 2, y), ln, font=fnt, fill=fill)
        y += fnt.size * 1.4
    return y

def make_slide(text_lines, slide_no, total, title, subtitle=None, accent=ACCENT):
    img = gradient_bg((W, H), BG_TOP, BG_BOT)
    d = ImageDraw.Draw(img)

    # 装飾: 左上と右下の半透明アクセント円
    d.ellipse([W - 300, -140, W + 160, 320], fill=(*accent,))
    d.ellipse([-180, H - 260, 220, H + 180], fill=(*accent,))
    # 半透明化のため別レイヤー合成
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([W - 300, -140, W + 160, 320], fill=(*accent, 28))
    od.ellipse([-180, H - 260, 220, H + 180], fill=(*accent, 24))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    # ステップラベル
    f_step = font(30, bold=True)
    step_label = f"STEP {slide_no} / {total}"
    d.text((56, 44), step_label, font=f_step, fill=accent if isinstance(accent, tuple) else ACCENT)

    # メインタイトル
    f_title = font(52, bold=True)
    d.text((56, 96), title, font=f_title, fill=TEXT)
    if subtitle:
        f_sub = font(30)
        d.text((56, 168), subtitle, font=f_sub, fill=MUTED)

    # 本文
    f_body = font(34)
    body_y = 260
    max_w = W - 112
    for ln in text_lines:
        fnt = f_body
        # 小見出し(***)は強調
        if ln.startswith("◆"):
            fnt = font(36, bold=True)
            wln = d.textlength(ln, font=fnt)
            d.text(((W - wln) / 2, body_y), ln, font=fnt, fill=accent if isinstance(accent, tuple) else ACCENT)
            body_y += fnt.size * 1.6
            continue
        lines = wrap(d, ln, fnt, max_w)
        for ll in lines:
            wll = d.textlength(ll, font=fnt)
            d.text(((W - wll) / 2, body_y), ll, font=fnt, fill=TEXT)
            body_y += fnt.size * 1.35
        body_y += 10

    # 下端のブランド
    d.text((56, H - 58), "ナレッジ化プロジェクト", font=font(24), fill=MUTED)
    return img

def slide_to_frames(img, sec):
    """1枚のスライドを A-B-A の軽いズームでフェード区間を除いた静止+ズームのフレーム列にする。
    ここではシンプルに、フェード用のアルファ進捗を返すだけにして、後で合成する。"""
    return sec

def encode_video(frames, out_path, fps=FPS):
    import subprocess, numpy as np
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for im in frames:
        proc.stdin.write(np.asarray(im.convert("RGB")).tobytes())
    proc.stdin.close()
    proc.wait()

def make_video(slides, out_name, slide_sec=SLIDE_SEC, fade_sec=FADE_SEC):
    """slides: list of PIL Image。各スライドを slide_sec 静止させ、間をフェードさせる。"""
    import numpy as np
    # 各スライドをフレーム列に
    per = int(slide_sec * FPS)
    fade_frames = int(fade_sec * FPS)
    all_frames = []
    for i, s in enumerate(slides):
        base = s.convert("RGB")
        for f in range(per):
            all_frames.append(base)
        # 次のスライドへのフェード(クロスフェード用に次のスライドを先読み)
        if i < len(slides) - 1:
            nxt = slides[i + 1].convert("RGB")
            for f in range(1, fade_frames + 1):
                t = f / fade_frames
                blended = Image.blend(base, nxt, t)
                all_frames.append(blended)
        else:
            # 最後は暗転で締める
            for f in range(1, fade_frames + 1):
                t = f / fade_frames
                blended = Image.blend(base, Image.new("RGB", (W, H), BG_TOP), t)
                all_frames.append(blended)
    out_path = os.path.join(OUTDIR, out_name)
    encode_video(all_frames, out_path)
    print("WROTE", out_path, len(all_frames), "frames")

# ============ 各 Step のスライド定義 ============

def step1_slides():
    return [
        make_slide(
            ["◆ 目指すのは「属人化の解消」",
             "",
             "ベテラン社員の中に溜まってしまった、",
             "個人しか知らない業務ノウハウ。",
             "引き継ぎ・後任育成・業務の標準化に役立てたい。"],
            slide_no=1, total=3, title="属人化した業務の「ナレッジ化」判定", subtitle="Step1：ナレッジ化チェックAI", accent=ACCENT),
        make_slide(
            ["◆ チェックAIが判定する",
             "",
             "その業務は「ナレッジ化すべき業務」なのか。",
             "暗黙知か・標準化できるか・属人度が高いか。",
             "現場の業務棚卸しに合わせて、AIが客観的に評価。"],
            slide_no=2, total=3, title="「ナレッジ化すべきか」を判定", subtitle="Step1：チェックAI", accent=ACCENT),
        make_slide(
            ["◆ 効果",
             "",
             "・膨大な業務の中から、優先すべきものを抽出",
             "・属人化の「見える化」で、対策の優先度が明確に",
             "・無駄なナレッジ化作業を減らし、工数削減"],
            slide_no=3, total=3, title="成果と効果", subtitle="Step1：まとめ", accent=ACCENT),
    ]

def step2_slides():
    return [
        make_slide(
            ["◆ インタビューから「集合知」へ",
             "",
             "質疑応答文書・その録音データから、",
             "業務スキルを「集合知(ナレッジ)」として形にする。"],
            slide_no=1, total=3, title="ベテランのスキルを集合知化", subtitle="Step2：インタビュー → ナレッジ化", accent=ACCENT2),
        make_slide(
            ["◆ アプリが行うこと",
             "",
             "・録音/文書の自動要約とテキスト化",
             "・ノウハウ・手順・判断基準を構造化",
             "・検索できるナレッジベースとして蓄積"],
            slide_no=2, total=3, title="質疑応答をナレッジに変換", subtitle="Step2：自動化", accent=ACCENT2),
        make_slide(
            ["◆ 効果",
             "",
             "・個人のスキルを組織の資産に変換",
             "・誰でも同じ知識にアクセス可能に",
             "・人材育成・標準化・業務継続性を向上"],
            slide_no=3, total=3, title="成果と効果", subtitle="Step2：まとめ", accent=ACCENT2),
    ]

def step3_slides():
    return [
        make_slide(
            ["◆ サンプル：見積書作成",  "",
             "見積書作成のナレッジを使って、",
             "「見積チェック」の属人化を解消するアプリを試作。"],
            slide_no=1, total=3, title="見積チェックアプリ", subtitle="Step3：PoC（サンプル実装）", accent=ACCENT),
        make_slide(
            ["◆ チェックポイント",
             "",
             "・単価・数量・項目漏れのチェック",
             "・過去の見積パターンとの差分を検出",
             "・ベテランの判断基準をナレッジとして適用"],
            slide_no=2, total=3, title="見積りの属人化を解消", subtitle="Step3：チェック内容", accent=ACCENT),
        make_slide(
            ["◆ 成果と今後の広がり",
             "",
             "・見積チェックの属人化を解消",
             "・この仕組みを他業務にも適用可能に",
             "・Step1・2のナレッジ基盤と連携"],
            slide_no=3, total=3, title="まとめ", subtitle="Step3：効果", accent=ACCENT),
    ]

if __name__ == "__main__":
    make_video(step1_slides(), "step1.mp4")
    make_video(step2_slides(), "step2.mp4")
    make_video(step3_slides(), "step3.mp4")
    print("DONE")
