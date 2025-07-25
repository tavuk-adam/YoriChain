from flask import Flask, render_template_string, request, session, redirect, url_for, jsonify
import random
import threading
import time

app = Flask(__name__)
app.secret_key = "gizli_tavuk"

lock = threading.Lock()

# YoriChain verileri
fiyat = 0
log_kaydi = []
simulasyon_aktif = False
kalan_sure = 0

# Meilleştirme seviyesi 0-5 (0=kapalı)
dusme_meille_seviye = 0
yukselme_meille_seviye = 0

HTML = '''
<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>💰 YORICHAIN</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background:#121212; color:#eee; }
    pre { background:#111; color:#0f0; padding:10px; height:200px; overflow:auto; font-family:monospace; }
    .fiyat { font-size:2rem; color:lime; }
  </style>
</head>
<body class="container py-4">
  <h1>💰 YORICHAIN</h1>

  {% if not session.get("giris_tavuk") %}
    <h2>⛓️ YoriChain</h2>
    <div>Fiyat: <span class="fiyat">{{ fiyat }}</span> elmas</div>

    <form method="post" action="/login" class="mt-4">
      <label>🔑 Şifre: <input type="password" name="password" class="form-control" required></label><br>
      <button class="btn btn-primary">Giriş Yap</button>
    </form>
  {% else %}

    <a href="/logout" class="btn btn-warning mb-4">🚪 Çıkış Yap</a>

    <h2>⛓️ YoriChain</h2>
    <label>⏳ Süre (sn): 
      <input type="number" id="sure_input" class="form-control mb-2" value="20" min="5" max="120">
    </label>
    <label>💰 Başlangıç Fiyatı (opsiyonel): 
      <input type="number" id="baslangic_input" class="form-control mb-2" placeholder="Boş bırakılırsa eski fiyatla devam" min="1">
    </label>
    <div>Fiyat: <span class="fiyat" id="fiyat">{{ fiyat }}</span> elmas</div>
    <div>Durum: <span id="durum">{{ durum }}</span></div>
    <div>Kalan Süre: <span id="kalan_sure">{{ kalan_sure }}</span> saniye</div>

    <div class="mb-3">
      <button id="dusme_arti" class="btn btn-danger">⬇️ Düşmeye Meilleştir (+)</button>
      <button id="dusme_eksi" class="btn btn-secondary">⬇️ Düşmeye Meilleştir (-)</button>
      <span>Düşme Seviyesi: <span id="dusme_seviye">{{ dusme_meille_seviye }}</span> / 5</span>
    </div>

    <div class="mb-3">
      <button id="yukselme_arti" class="btn btn-success">⬆️ Yükselmeye Meilleştir (+)</button>
      <button id="yukselme_eksi" class="btn btn-secondary">⬆️ Yükselmeye Meilleştir (-)</button>
      <span>Yükselme Seviyesi: <span id="yukselme_seviye">{{ yukselme_meille_seviye }}</span> / 5</span>
    </div>

    <button id="devamBtn" class="btn btn-success my-1">▶ Devam</button>
    <button id="durdurBtn" class="btn btn-danger my-1">⏹ Durdur</button>
    <button id="temizleBtn" class="btn btn-secondary my-1">🧹 Temizle</button>
    <pre id="log">{{ log }}</pre>

  {% endif %}

<script>
  function update() {
    fetch('/status').then(r => r.json()).then(data => {
      if(document.getElementById("fiyat")) document.getElementById("fiyat").textContent = data.fiyat;
      if(document.getElementById("durum")) document.getElementById("durum").textContent = data.durum;
      if(document.getElementById("log")) document.getElementById("log").textContent = data.log;
      if(document.getElementById("kalan_sure")) document.getElementById("kalan_sure").textContent = data.kalan_sure;

      if(document.getElementById("dusme_seviye")) document.getElementById("dusme_seviye").textContent = data.dusme_meille_seviye;
      if(document.getElementById("yukselme_seviye")) document.getElementById("yukselme_seviye").textContent = data.yukselme_meille_seviye;
    });
  }

  setInterval(update, 1000);
  update();

  // YoriChain CONTROLS
  if (document.getElementById("devamBtn")) {
    document.getElementById("devamBtn").onclick = () => {
      const sure = parseInt(document.getElementById("sure_input")?.value) || 20;
      const baslangic = parseInt(document.getElementById("baslangic_input")?.value);
      fetch('/devam', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ sure: sure, baslangic: baslangic })
      });
    };
  }
  if (document.getElementById("durdurBtn")) {
    document.getElementById("durdurBtn").onclick = () => fetch('/durdur', { method: 'POST' });
  }
  if (document.getElementById("temizleBtn")) {
    document.getElementById("temizleBtn").onclick = () => fetch('/temizle', { method: 'POST' });
  }

  // Meilleştirme artır/azalt butonları
  if(document.getElementById("dusme_arti")) {
    document.getElementById("dusme_arti").onclick = () => {
      fetch('/meille_dusme_artir', { method: 'POST' });
    };
  }
  if(document.getElementById("dusme_eksi")) {
    document.getElementById("dusme_eksi").onclick = () => {
      fetch('/meille_dusme_azalt', { method: 'POST' });
    };
  }
  if(document.getElementById("yukselme_arti")) {
    document.getElementById("yukselme_arti").onclick = () => {
      fetch('/meille_yukselme_artir', { method: 'POST' });
    };
  }
  if(document.getElementById("yukselme_eksi")) {
    document.getElementById("yukselme_eksi").onclick = () => {
      fetch('/meille_yukselme_azalt', { method: 'POST' });
    };
  }
</script>
</body>
</html>
'''


def simulasyonu_baslat(sure, baslangic=None):
    global fiyat, log_kaydi, simulasyon_aktif, kalan_sure
    global dusme_meille_seviye, yukselme_meille_seviye
    with lock:
        if baslangic and isinstance(baslangic, int) and baslangic > 0:
            fiyat = baslangic
        simulasyon_aktif = True
        kalan_sure = sure

    for saniye in range(1, sure + 1):
        time.sleep(1)
        with lock:
            if not simulasyon_aktif:
                log_kaydi.append("⏹ Simülasyon erken durduruldu.")
                break

            # Meilleştirme etkisi
            # Normalde -2, -1, 0, 1, 2 eşit olasılıkta
            # Meilleştirme ile olasılıkları değiştireceğiz:
            # Olabilir -2 ve 2'nin ağırlıklarını arttıracağız seviyeye göre

            olasiliklar = [-2, -1, 0, 1, 2]

            # Her olasılık için ağırlık başlangıçta eşit (1)
            agirliklar = [1, 1, 1, 1, 1]

            # Düşmeye meilleştirme: -2, -1 ağırlıkları artar
            if dusme_meille_seviye > 0:
                agirliklar[0] += dusme_meille_seviye  # -2
                agirliklar[1] += dusme_meille_seviye  # -1

            # Yükselmeye meilleştirme: 1, 2 ağırlıkları artar
            if yukselme_meille_seviye > 0:
                agirliklar[3] += yukselme_meille_seviye  # 1
                agirliklar[4] += yukselme_meille_seviye  # 2

            # Normalleştirilmiş weighted seçim
            toplam_agirlik = sum(agirliklar)
            secim = random.choices(olasiliklar, weights=agirliklar, k=1)[0]

            fiyat = max(1, fiyat + secim)

            log_kaydi.append(
                f"{saniye}. saniye - fiyat: {fiyat} elmas (Düşme Meille: {dusme_meille_seviye}, Yükselme Meille: {yukselme_meille_seviye})")

            kalan_sure -= 1

    with lock:
        simulasyon_aktif = False
        kalan_sure = 0
        log_kaydi.append("⏹ Simülasyon durdu.")


@app.route("/")
def index():
    return render_template_string(HTML,
                                  fiyat=fiyat, log="\n".join(log_kaydi), durum="🟢" if simulasyon_aktif else "🔴",
                                  kalan_sure=kalan_sure,
                                  dusme_meille_seviye=dusme_meille_seviye,
                                  yukselme_meille_seviye=yukselme_meille_seviye,
                                  session=session)


@app.route("/status")
def status():
    return jsonify({
        "fiyat": fiyat,
        "log": "\n".join(log_kaydi[-50:]),
        "durum": "🟢" if simulasyon_aktif else "🔴",
        "kalan_sure": kalan_sure,
        "simulasyon_aktif": simulasyon_aktif,
        "dusme_meille_seviye": dusme_meille_seviye,
        "yukselme_meille_seviye": yukselme_meille_seviye,
    })


@app.route("/devam", methods=["POST"])
def devam():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    data = request.get_json(force=True)
    sure = data.get("sure", 20)
    baslangic = data.get("baslangic")
    try:
        sure = int(sure)
    except:
        sure = 20
    if sure < 5 or sure > 120:
        sure = 20
    try:
        baslangic = int(baslangic)
    except:
        baslangic = None
    threading.Thread(target=simulasyonu_baslat, args=(sure, baslangic)).start()
    return ('', 204)


@app.route("/durdur", methods=["POST"])
def durdur():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global simulasyon_aktif
    with lock:
        simulasyon_aktif = False
    return ('', 204)


@app.route("/temizle", methods=["POST"])
def temizle():
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    global log_kaydi
    with lock:
        log_kaydi.clear()
        log_kaydi.append("🧹 Log temizlendi.")
    return ('', 204)


# Meilleştirme artır / azalt rotaları
@app.route("/meille_dusme_artir", methods=["POST"])
def meille_dusme_artir():
    global dusme_meille_seviye, yukselme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if dusme_meille_seviye < 5:
            dusme_meille_seviye += 1
        # Yükselmeye meilleştirme kapalı olur (ters etki olmasın)
        if yukselme_meille_seviye != 0:
            yukselme_meille_seviye = 0
    return ('', 204)


@app.route("/meille_dusme_azalt", methods=["POST"])
def meille_dusme_azalt():
    global dusme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if dusme_meille_seviye > 0:
            dusme_meille_seviye -= 1
    return ('', 204)


@app.route("/meille_yukselme_artir", methods=["POST"])
def meille_yukselme_artir():
    global yukselme_meille_seviye, dusme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if yukselme_meille_seviye < 5:
            yukselme_meille_seviye += 1
        # Düşmeye meilleştirme kapalı olur (ters etki olmasın)
        if dusme_meille_seviye != 0:
            dusme_meille_seviye = 0
    return ('', 204)


@app.route("/meille_yukselme_azalt", methods=["POST"])
def meille_yukselme_azalt():
    global yukselme_meille_seviye
    if not session.get("giris_tavuk"):
        return "Yetkisiz", 403
    with lock:
        if yukselme_meille_seviye > 0:
            yukselme_meille_seviye -= 1
    return ('', 204)


@app.route("/login", methods=["POST"])
def login():
    sifre = request.form.get("password")
    if sifre == "yoriichi123":
        session["giris_tavuk"] = True
        log_kaydi.append("✅ YoriChain giriş yapıldı.")
    else:
        log_kaydi.append("🚫 Hatalı şifre denemesi!")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("giris_tavuk", None)
    log_kaydi.append("👋 Çıkış yapıldı.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
