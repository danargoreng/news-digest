# Ringkasan Berita Harian (Prototipe)

Mengambil berita 24 jam terakhir dari RSS media nasional & internasional, memberi kategori + tag,
mengelompokkan berita yang membahas peristiwa sama, membuat ringkasan netral 2-4 kalimat
(Bahasa Indonesia), menyimpan ke SQLite, dan menampilkannya di web lokal.

## Struktur folder

```
news-digest/
├── config.yaml            <- SEMUA pengaturan + daftar sumber berita (edit di sini)
├── .env.example           <- contoh file rahasia (salin jadi .env, isi API key)
├── requirements.txt       <- daftar library Python
├── run_pipeline.py        <- jalankan proses sekali (ambil -> olah -> simpan)
├── app.py                 <- web Flask + jadwal otomatis 07.00 WIB
├── newsdigest/
│   ├── config.py          <- membaca config.yaml, daftar kategori
│   ├── fetcher.py         <- mengambil & membersihkan data RSS
│   ├── llm.py             <- koneksi ke LLM (API ala OpenAI) + embedding
│   ├── classifier.py      <- kategori + tag per artikel (batch)
│   ├── clustering.py      <- mengelompokkan peristiwa yang sama
│   ├── summarizer.py      <- ringkasan netral per cluster + filter angka pasar
│   ├── pipeline.py        <- merangkai semua langkah di atas
│   └── db.py              <- SQLite (simpan & query, arsip per tanggal)
├── templates/index.html   <- halaman web
├── static/style.css       <- tampilan
└── data/                  <- tempat file news.db dibuat otomatis
```

## Instalasi (langkah demi langkah)

Butuh Python 3.10 atau lebih baru (cek: `python --version`).

1. Buka terminal / Command Prompt, masuk ke folder proyek:
   ```
   cd news-digest
   ```
2. Buat virtual environment:
   - Windows: `python -m venv venv` lalu `venv\Scripts\activate`
   - Mac/Linux: `python3 -m venv venv` lalu `source venv/bin/activate`
3. Pasang library:
   ```
   pip install -r requirements.txt
   ```
4. Siapkan API key:
   - Salin `.env.example` menjadi `.env` (Windows: `copy .env.example .env`, Mac/Linux: `cp .env.example .env`)
   - Buka `.env`, ganti teks setelah `OPENAI_API_KEY=` dengan API key Anda.
5. (Opsional) ganti model/penyedia LLM di bagian `llm:` pada `config.yaml`.

## Menjalankan

1. Ambil & olah berita (pertama kali, butuh beberapa menit):
   ```
   python run_pipeline.py
   ```
   Di akhir akan tampil laporan: berapa artikel per sumber, atau sumber mana yang gagal.
2. Jalankan web:
   ```
   python app.py
   ```
   Buka http://127.0.0.1:5000 di browser.

`python app.py` juga mengaktifkan jadwal otomatis **setiap hari 07.00 WIB**, selama program
tetap berjalan (komputer menyala). Jika ingin tanpa jadwal di dalam app, set
`DISABLE_SCHEDULER=1` lalu pakai cron:

```
0 7 * * *  cd /path/ke/news-digest && /path/ke/venv/bin/python run_pipeline.py >> data/cron.log 2>&1
```
(Cron memakai jam server; pastikan server berzona WIB atau sesuaikan jamnya.)

Menjalankan `run_pipeline.py` dua kali pada tanggal yang sama akan menggantikan data hari itu.
Arsip tanggal sebelumnya tetap ada dan bisa dipilih di dropdown tanggal.

## Cara menambah / menghapus sumber RSS

Buka `config.yaml`, bagian `sources:`. Untuk menambah, salin satu blok dan ubah isinya:

```yaml
  - name: CNN Indonesia
    scale: nasional          # atau: internasional
    url: "https://www.cnnindonesia.com/nasional/rss"
```

Untuk menghapus, hapus blok tiga baris sumber tersebut. Tidak ada kode yang perlu diubah.
Simpan file, lalu jalankan ulang `python run_pipeline.py`.

## Penjelasan singkat fungsi penting

| File | Fungsi | Tugas |
|---|---|---|
| fetcher.py | `fetch_source` | Unduh satu feed, ambil judul + link + snippet 24 jam terakhir |
| fetcher.py | `fetch_all` | Loop semua sumber; error satu sumber hanya dicatat, lalu lanjut; buang duplikat |
| classifier.py | `classify_articles` | Kirim judul + snippet per batch ke LLM, terima kategori + 2-4 tag |
| clustering.py | `cluster_articles` | Embedding + cosine similarity (atau kemiripan judul), urut by jumlah media |
| summarizer.py | `summarize_clusters` | Ringkasan 2-4 kalimat per cluster, per batch |
| summarizer.py | `sanitize` | Membuang kalimat yang memuat angka pasar (IHSG, kurs, saham, dll.) |
| db.py | `save_run` / `query_clusters` | Simpan hasil per tanggal / ambil dengan filter kategori, skala, kata kunci |
| pipeline.py | `run_pipeline` | Merangkai semua langkah |
| app.py | `index`, `start_scheduler` | Halaman web + jadwal harian |

## Catatan & batasan prototipe

- **Hanya judul + snippet RSS** yang dipakai; isi artikel penuh tidak diambil. Snippet hanya dikirim
  ke LLM dan tidak disimpan ke database; yang tersimpan: judul, link, ringkasan, kategori, tag.
- **Reuters** tidak punya RSS resmi lagi, jadi memakai Google News RSS (difilter ke reuters.com).
  Snippet-nya biasanya kosong, jadi akurasi kategori/cluster untuk sumber ini bergantung pada judul.
- **URL RSS media bisa berubah** dan sebagian tidak bisa saya uji dari sini. Jika satu sumber gagal,
  aplikasi tetap jalan; perbaiki URL-nya di `config.yaml`.
- **Angka pasar**: LLM diminta tidak menyebutnya, ditambah filter otomatis. Filter ini sederhana,
  jadi tetap baca hasilnya dengan kritis.
- **Clustering** memakai metode greedy sederhana. Atur `similarity_threshold` di `config.yaml`
  bila hasil terlalu longgar/ketat. Jika penyedia LLM Anda tidak punya API embedding, ubah
  `method` menjadi `"judul"`.
- Ringkasan dihasilkan LLM dan bisa keliru; gunakan tautan sumber untuk verifikasi.
- Web ini hanya untuk penggunaan lokal (tanpa login), jangan dibuka ke internet apa adanya.
