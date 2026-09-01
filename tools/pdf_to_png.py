#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_to_png.py — 화면 PDF를 PNG로 바꾸는 도구 (Q-Page 자격정보집)

쓰는 법
  python tools/pdf_to_png.py pdf dist/sheets --dpi 200
  → pdf/ 안의 종목별 PDF가 dist/sheets/종목코드.png 로 바뀐다.

파일명 규칙 (엑셀에서 PDF를 저장할 때)
  pdf/1530.pdf · pdf/1530_식품기사.pdf · pdf/C521.pdf 전부 인식한다.
  파일명 맨 앞 덩어리(숫자 3~5자리, 과정형은 C+숫자)를 종목코드로 쓴다.
  ★ 반드시 One-page(외부용) 시트에서 출력한 PDF만 넣을 것. 내부용 금지.

변환 엔진 (Q-RADAR build_site.py와 같은 계열)
  1순위: pdftoppm(poppler) + pngquant   — 실측 200dpi 75KB/장
  2순위: PyMuPDF + Pillow 팔레트         — 실측 200dpi 88KB/장
  poppler가 없으면(윈도우 등) 자동으로 2순위로 내려간다.

왜 200dpi인가
  A4 기준 1653×2339px. 폰에서 2배 확대까지 글자가 버틴다.
  감색 손실 실측: pngquant 평균 오차 0.19/255 — 눈으로 구분되지 않는다.
  652종목 전량 약 48MB (GitHub Pages 1GB의 4.7%)

증분 변환
  결과 폴더의 manifest.json에 원본 PDF의 크기·수정시각과 변환 옵션을
  적어 두고, 안 바뀐 PDF는 건너뛴다. 없어진 종목의 PNG는 지운다.
  --overwrite 를 주면 전부 다시 만든다. --dpi 등 옵션이 바뀌어도 전부 다시 만든다.

쪽수
  기본은 첫 쪽만 PNG로 만든다(화면 미리보기 용도).
  --pages all 을 주면 모든 쪽을 종목코드.png, 종목코드-2.png … 로 만든다.

설치
  리눅스/Actions : apt-get install poppler-utils pngquant
  윈도우(폴백)   : pip install pymupdf pillow
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

# ── 엔진 탐지 ────────────────────────────────────────────────

def _have(cmd):
    return shutil.which(cmd) is not None

HAVE_POPPLER = _have("pdftoppm")
HAVE_PNGQUANT = _have("pngquant")

# 폴백 엔진은 필요할 때만 불러온다(윈도우에서 poppler 없이 돌릴 때)
_pymupdf = _Image = None

def _load_fallback(required=True):
    global _pymupdf, _Image
    if _pymupdf is None:
        try:
            import pymupdf as m
        except ImportError:
            try:
                import fitz as m
            except ImportError:
                if required:
                    sys.exit("변환 엔진이 없습니다.\n"
                             "  리눅스: apt-get install poppler-utils pngquant\n"
                             "  윈도우: pip install pymupdf pillow")
                return None, None
        try:
            from PIL import Image as I
        except ImportError:
            if required:
                sys.exit("Pillow가 없습니다. pip install pillow")
            return None, None
        _pymupdf, _Image = m, I
    return _pymupdf, _Image


# ── 종목코드 인식 ────────────────────────────────────────────
# 1530.pdf / 1530_식품기사.pdf / C521.pdf / c521_테스트.pdf 모두 인식
CODE_RE = re.compile(r"^([A-Za-z]?\d{3,5})(?:[_\-].*)?$")

def code_of(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    m = CODE_RE.match(stem)
    return m.group(1).upper() if m else None


# ── 변환 ────────────────────────────────────────────────────

def _pages_of(pdf_path):
    """쪽 수만 센다. pdfinfo가 있으면 그걸로, 없으면 폴백 엔진으로."""
    if _have("pdfinfo"):
        try:
            r = subprocess.run(["pdfinfo", pdf_path],
                               capture_output=True, text=True, timeout=30)
            for line in r.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split()[1])
        except Exception:
            pass
    m, _ = _load_fallback(required=False)
    if m is not None:
        try:
            d = m.open(pdf_path); n = d.page_count; d.close()
            return n
        except Exception:
            pass
    return 1


def _quantize(png_path, colors):
    """pngquant 감색. 품질을 못 맞추면 pngquant는 아무것도 쓰지 않는다 → 원본 유지."""
    if not (colors and HAVE_PNGQUANT):
        return
    tmp = png_path + ".q"
    r = subprocess.run(["pngquant", "--force", "--quality", "60-90",
                        "--speed", "1", "--output", tmp, png_path],
                       capture_output=True, timeout=120)
    if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        os.replace(tmp, png_path)
    elif os.path.exists(tmp):
        os.remove(tmp)


def _out_name(code, page_no):
    """1쪽은 종목코드.png, 2쪽부터는 종목코드-2.png …  (기존 주소가 안 깨지게)"""
    return f"{code}.png" if page_no == 1 else f"{code}-{page_no}.png"


def convert_one(pdf_path, dst_dir, code, dpi, colors, pages_mode):
    """PDF 한 건을 PNG로. (쪽수, 만든 파일 목록, 총 바이트) 반환."""
    pages = _pages_of(pdf_path)
    last = pages if pages_mode == "all" else 1
    made = []

    if HAVE_POPPLER:
        for p in range(1, last + 1):
            out_path = os.path.join(dst_dir, _out_name(code, p))
            stem = os.path.splitext(out_path)[0]
            subprocess.run(["pdftoppm", "-png", "-r", str(dpi),
                            "-f", str(p), "-l", str(p),
                            "-singlefile", pdf_path, stem],
                           check=True, timeout=120)
            _quantize(out_path, colors)
            made.append(os.path.basename(out_path))
    else:
        # ── 폴백: PyMuPDF + Pillow 팔레트 ──
        m, I = _load_fallback()
        doc = m.open(pdf_path)
        for p in range(1, min(last, doc.page_count) + 1):
            out_path = os.path.join(dst_dir, _out_name(code, p))
            pix = doc.load_page(p - 1).get_pixmap(dpi=dpi)
            img = I.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if colors:
                img = img.convert("P", palette=I.ADAPTIVE,
                                  colors=colors, dither=I.NONE)
            img.save(out_path, "PNG", optimize=True)
            made.append(os.path.basename(out_path))
        doc.close()

    total = sum(os.path.getsize(os.path.join(dst_dir, f)) for f in made)
    return pages, made, total


# ── 본체 ────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="화면 PDF → PNG (Q-Page)")
    ap.add_argument("src", help="PDF 폴더 (예: pdf)")
    ap.add_argument("dst", help="PNG 결과 폴더 (예: dist/sheets)")
    ap.add_argument("--dpi", type=int, default=200,
                    help="해상도. 기본 200 — 폰에서 2배 확대까지 글자가 버틴다")
    ap.add_argument("--colors", type=int, default=256,
                    help="0이면 감색 없이 원본 색 그대로")
    ap.add_argument("--pages", choices=["first", "all"], default="first",
                    help="first=첫 쪽만(기본) · all=모든 쪽")
    ap.add_argument("--overwrite", action="store_true",
                    help="바뀌지 않은 PDF까지 전부 다시 변환")
    a = ap.parse_args()

    if not os.path.isdir(a.src):
        sys.exit(f"PDF 폴더가 없습니다: {a.src}")
    os.makedirs(a.dst, exist_ok=True)

    man_path = os.path.join(a.dst, "manifest.json")
    opts_now = {"dpi": a.dpi, "colors": a.colors, "pages": a.pages}
    old_man, old_opts = {}, {}
    if os.path.exists(man_path):
        try:
            j = json.load(open(man_path, encoding="utf-8"))
            old_man, old_opts = j.get("items", {}), j.get("options", {})
        except Exception:
            pass

    full_redo = a.overwrite
    if old_man and old_opts != opts_now:
        print(f"  옵션이 바뀌어 전량 다시 변환합니다 ({old_opts} → {opts_now})")
        full_redo = True

    # PDF 목록 수집 (같은 종목코드가 두 번 나오면 첫 파일만 쓰고 경고)
    pdfs, dup = {}, []
    for fn in sorted(os.listdir(a.src)):
        if not fn.lower().endswith(".pdf"):
            continue
        c = code_of(fn)
        if c is None:
            print(f"  ⚠ 종목코드를 못 읽어 건너뜀: {fn}")
            continue
        if c in pdfs:
            dup.append(fn)
            continue
        pdfs[c] = fn
    for fn in dup:
        print(f"  ⚠ 같은 종목코드 PDF가 이미 있어 건너뜀: {fn}")

    t0 = time.time()
    total = skipped = failed = 0
    bytes_sum = 0
    new_man = {}

    for code, fn in pdfs.items():
        src_path = os.path.join(a.src, fn)
        st = os.stat(src_path)
        sig = {"size": st.st_size, "mtime": int(st.st_mtime)}
        prev = old_man.get(code)
        prev_ok = (prev and prev.get("size") == sig["size"]
                   and prev.get("mtime") == sig["mtime"]
                   and all(os.path.exists(os.path.join(a.dst, f))
                           for f in prev.get("files", [])))
        if prev_ok and not full_redo:
            new_man[code] = prev
            skipped += 1
            continue
        try:
            pages, files, nbytes = convert_one(src_path, a.dst, code,
                                               a.dpi, a.colors, a.pages)
            new_man[code] = dict(sig, pages=pages, files=files, bytes=nbytes)
            total += 1
            bytes_sum += nbytes
        except Exception as e:
            failed += 1
            print(f"  ✗ 실패: {fn} — {e}")

    # 이번에 없어진 종목의 PNG는 지운다(엑셀에서 종목이 빠진 경우)
    keep = {f for v in new_man.values() for f in v.get("files", [])}
    stale = [f for f in os.listdir(a.dst)
             if f.endswith(".png") and f not in keep]
    for f in stale:
        os.remove(os.path.join(a.dst, f))

    json.dump({"options": opts_now, "items": new_man},
              open(man_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)

    dt = time.time() - t0
    print("\n[변환 결과]")
    eng = ("pdftoppm" + (" + pngquant" if (a.colors and HAVE_PNGQUANT) else "")) \
          if HAVE_POPPLER else "PyMuPDF + Pillow"
    print(f"  해상도 {a.dpi}dpi · 엔진 {eng}"
          + ("" if a.colors else " · 감색 없음")
          + ("" if a.pages == "first" else " · 모든 쪽"))
    if HAVE_POPPLER and a.colors and not HAVE_PNGQUANT:
        print("  ⚠ pngquant가 없어 감색을 못 했습니다. "
              "apt-get install pngquant 를 권합니다(용량 3배 차이)")
    print(f"  변환 {total}장 · 그대로 {skipped} · 삭제 {len(stale)} · "
          f"실패 {failed} · {dt:.0f}초")
    if stale:
        print(f"      삭제된 PNG: {', '.join(sorted(stale)[:8])}"
              f"{' …' if len(stale) > 8 else ''}")
    all_png = [f for f in os.listdir(a.dst) if f.endswith(".png")]
    all_bytes = sum(os.path.getsize(os.path.join(a.dst, f)) for f in all_png)
    print(f"  보유 {len(all_png)}장 · 합계 {all_bytes/1048576:.0f}MB"
          f" ({all_bytes/1073741824*100:.1f}% of GitHub Pages 1GB)")
    if total:
        print(f"  이번 변환 평균 {bytes_sum/total/1024:.0f}KB")
    if all_bytes / 1073741824 > 0.5:
        print("  ⚠ 합계가 1GB 한도의 절반을 넘었습니다. "
              "--dpi 를 낮추는 것을 검토하세요.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
