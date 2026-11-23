"""Claude Code PreToolUse kancası: kasa ve kayıt korumaları.

Ajanların şunları yapmasını engeller:
- .kasa_acik dosyasını oluşturmak veya silmek (kasayı sadece insan açar)
- ayarlar.json dosyasını değiştirmek (kasa tarihi kaydırılamaz)
- kayit/denemeler.csv dosyasına elle yazmak (sadece test motoru yazar)
- kasa kapalıyken test motorunu --kasa ile çalıştırmak

Bu bir emniyet kemeridir, kasa değildir: kararlı bir ajan başka yollar
bulabilir. Asıl denetim izi git geçmişidir.

Çıkış kodu 2 = işlemi engelle; stderr mesajı Claude'a iletilir.
"""
import json
import os
import re
import sys

KORUNAN_YAZMA = ("ayarlar.json", "denemeler.csv", ".kasa_acik")
YAZMA_IPUCLARI = (">", "tee ", "sed -i", "mv ", "cp ", "rm ", "touch ", "truncate",
                  "Set-Content", "Out-File", "Add-Content", "Remove-Item", "New-Item",
                  "open(", "write_text", "to_csv")


def engelle(mesaj: str) -> None:
    print(f"KORUMA: {mesaj}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        veri = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    arac = veri.get("tool_name", "")
    girdi = veri.get("tool_input", {}) or {}
    proje = os.environ.get("CLAUDE_PROJECT_DIR") or veri.get("cwd") or os.getcwd()

    if arac in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        yol = str(girdi.get("file_path") or girdi.get("notebook_path") or "").replace("\\", "/")
        for korunan in KORUNAN_YAZMA:
            if yol.endswith(korunan):
                engelle(f"{korunan} dosyası ajanlar tarafından değiştirilemez. "
                        "Bu dosya insan veya test motoru içindir.")

    elif arac in ("Bash", "PowerShell"):
        komut = str(girdi.get("command", ""))
        if ".kasa_acik" in komut:
            engelle("Kasayı sadece insan açabilir. .kasa_acik dosyasına dokunma.")
        if "denemeler.csv" in komut:
            engelle("kayit/denemeler.csv sadece test motoru tarafından yazılır; "
                    "okumak için Read aracını kullan.")
        if "ayarlar.json" in komut and any(i in komut for i in YAZMA_IPUCLARI):
            engelle("ayarlar.json değiştirilemez (kasa tarihi sabit kalmalı).")
        if re.search(r"test_et\.py.*--kasa\b", komut):
            if not os.path.exists(os.path.join(proje, ".kasa_acik")):
                engelle("Kasa kapalı. Kasa doğrulaması için insanın proje kökünde "
                        ".kasa_acik dosyası oluşturması gerekir.")

    sys.exit(0)


if __name__ == "__main__":
    main()
