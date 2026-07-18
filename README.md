# Türkçe-Rusça Çeviri Botu — Kurulum

Bu bot bir gruba eklendiğinde, Rusça yazılan her mesajı otomatik olarak Türkçeye,
Türkçe yazılan her mesajı da Rusçaya çevirip **orijinal mesaja yanıt (reply)
olarak** gönderir. Elle bir şey yapmana gerek yok.

## 1. BotFather ile bot oluşturma (senin yapman gereken kısım)

1. Telegram'da **@BotFather**'ı aç.
2. `/newbot` yaz, bot için bir isim ve kullanıcı adı belirle.
3. Sana bir **token** verecek (örnek: `123456:ABC-DEF...`). Bunu bir yere kaydet,
   birazdan lazım olacak.
4. Aynı sohbette `/setprivacy` yaz, botunu seç, **Disable** seçeneğini seç.
   - Bu adım kritik: privacy mode kapalı olmazsa bot grup içindeki mesajları
     göremez, sadece kendine yazılan komutları görür.
5. Botu, ikinizin de olduğu bir Telegram **grubuna** ekle.

## 2. Çeviri için hiçbir kayıt gerekmiyor

Bot, Google Translate'i kullanan ücretsiz bir kütüphane (`deep-translator`) ile
çalışıyor. Hiçbir yerde hesap açman, kart girmen veya key alman gerekmiyor.

## 3. Kodu GitHub'a yükleme (telefondan)

1. https://github.com adresinde bir hesabın yoksa aç.
2. Sağ üstten **New repository** ile boş bir repo oluştur (örn: `ceviri-botu`).
3. Repo sayfasında **Add file → Upload files** ile bu klasördeki
   `bot.py`, `requirements.txt` ve `Procfile` dosyalarını yükle, commit et.
   (Telefon tarayıcısından da sorunsuz çalışır.)

## 4. Railway'de yayına alma (telefondan)

1. https://railway.app adresine git, GitHub hesabınla giriş yap.
2. **New Project → Deploy from GitHub repo** ile az önce oluşturduğun
   `ceviri-botu` reposunu seç.
3. Railway kodu otomatik algılayıp deploy etmeye başlayacak.
4. Projeye gir → **Variables** sekmesinden şu değişkeni ekle:
   - `TELEGRAM_BOT_TOKEN` → BotFather'dan aldığın token
5. Değişkeni ekledikten sonra Railway otomatik yeniden başlatır.
   **Deployments** sekmesinden loglara bakıp
   `Bot başlatıldı, mesajlar dinleniyor...` satırını görürsen bot çalışıyor demektir.

Bundan sonra hiçbir şey yapmana gerek yok — bot 7/24 Railway üzerinde çalışır,
telefonunun açık olması gerekmez.

## Notlar

- Railway'in ücretsiz katmanında aylık belirli bir kullanım kotası var
  (küçük bir bot için normalde yeterli olur); kota dolarsa bana haber ver,
  alternatif ücretsiz bir platforma (Render gibi) geçebiliriz.
- Bot şu an mesajın Kiril alfabesi (Rusça harfler) içerip içermediğine bakarak
  dili anlıyor. İki dil dışında bir şey yazılmadığı sürece güvenilir çalışır.
