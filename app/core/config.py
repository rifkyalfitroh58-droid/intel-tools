"""OSINT Intelligence Suite — config.py — Konfigurasi terpusat"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), ".env"))
except ImportError:
    pass

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH      = os.path.join(os.getenv("STREAMLIT_DATA_DIR", "/tmp"), "osint_suite.db")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "isi_api_key_kamu_di_sini")

# ── Module colours — flat hex string ─────────────────────────────────────────
MODULE_COLORS = {
    "person": "#4FC3F7",
    "threat": "#E74C3C",
    "geo":    "#2ECC71",
    "media":  "#F39C12",
}
# Detail bg/border untuk komponen CSS
MODULE_COLOR_DETAIL = {
    "person": {"primary":"#4FC3F7","bg":"rgba(79,195,247,.1)","border":"rgba(79,195,247,.3)"},
    "threat": {"primary":"#E74C3C","bg":"rgba(231,76,60,.1)","border":"rgba(231,76,60,.3)"},
    "geo":    {"primary":"#2ECC71","bg":"rgba(46,204,113,.1)","border":"rgba(46,204,113,.3)"},
    "media":  {"primary":"#F39C12","bg":"rgba(243,156,18,.1)","border":"rgba(243,156,18,.3)"},
}
MODULE_LABELS = {"person":"Person Intel","threat":"Threat Intel","geo":"Geo Intel","media":"Media Intel"}
MODULE_ICONS  = {"person":"◈","threat":"⚠","geo":"◉","media":"◎"}
LINK_THRESHOLDS = {"person":0,"threat":40,"geo":1,"media":2}

# ── Plotly dark theme — dipakai semua modul ──────────────────────────────────
PLOT_THEME = {
    "paper_bgcolor": "#070d14",
    "plot_bgcolor":  "#070d14",
    "font":          {"family": "DM Mono, monospace", "color": "rgba(255,255,255,.7)", "size": 11},
}
# Gunakan PLOT_AXIS jika perlu default axis/legend/margin
PLOT_AXIS = {
    "gridcolor": "rgba(255,255,255,.05)",
    "linecolor":  "rgba(255,255,255,.1)",
    "tickfont":   {"size": 10},
    "showgrid":   True,
}
PLOT_LEGEND = {"bgcolor": "rgba(0,0,0,0)", "font": {"size": 10}}
PLOT_MARGIN = {"l": 40, "r": 20, "t": 40, "b": 40}
PLOT_COLORWAY = ["#4FC3F7","#E74C3C","#2ECC71","#F39C12","#9B59B6","#1ABC9C"]

# ── Threat categories ─────────────────────────────────────────────────────────
THREAT_CATEGORIES = {
    "HOAX":     {"label": "Hoaks / Disinformasi", "color": "#E74C3C", "icon": "🔴"},
    "HATE":     {"label": "Ujaran Kebencian",      "color": "#E67E22", "icon": "🟠"},
    "PROVOK":   {"label": "Provokasi",             "color": "#F39C12", "icon": "🟡"},
    "THREAT":   {"label": "Ancaman Keamanan",      "color": "#9B59B6", "icon": "🟣"},
    "NORMAL":   {"label": "Normal",                "color": "#2ECC71", "icon": "🟢"},
}

THREAT_LEVELS = {
    "CRITICAL":(80,100,"🔴 KRITIS","#E74C3C"),
    "HIGH":(60,79,"🟠 TINGGI","#E67E22"),
    "MEDIUM":(40,59,"🟡 SEDANG","#F39C12"),
    "LOW":(0,39,"🟢 RENDAH","#2ECC71"),
}
RISK_LEVELS = {
    "HIGH":(70,100,"🔴 TINGGI","#E74C3C"),
    "MEDIUM":(40,69,"🟡 SEDANG","#F39C12"),
    "LOW":(0,39,"🟢 RENDAH","#2ECC71"),
}
ENTITY_COLORS  = {"PERSON":"#E74C3C","ORG":"#3498DB","GPE":"#2ECC71","MONEY":"#F39C12","EVENT":"#9B59B6","PRODUCT":"#1ABC9C"}
ENTITY_LABELS  = {"PERSON":"Individu","ORG":"Organisasi","GPE":"Lokasi/Negara","MONEY":"Finansial","EVENT":"Kejadian","PRODUCT":"Produk"}
INCIDENT_TYPES = {
    "BENCANA":  {"label":"Bencana Alam",    "color":"#E74C3C","icon":"🌊"},
    "KONFLIK":  {"label":"Konflik Sosial",  "color":"#E67E22","icon":"⚔"},
    "KRIMINAL": {"label":"Kriminal",        "color":"#9B59B6","icon":"🔫"},
    "POLITIK":  {"label":"Politik",         "color":"#3498DB","icon":"🏛"},
    "EKONOMI":  {"label":"Ekonomi",         "color":"#F39C12","icon":"💰"},
    "KESEHATAN":{"label":"Kesehatan",       "color":"#2ECC71","icon":"🏥"},
    "LAINNYA":  {"label":"Lainnya",         "color":"#95A5A6","icon":"📌"},
}
HOAX_KEYWORDS = ["terbukti","faktanya","yang sebenarnya","disembunyikan","rahasia","konspirasi",
    "agenda tersembunyi","vaksin berbahaya","plandemi","segera sebarkan",
    "jangan sampai terhapus","kecurangan pemilu","suara dicuri","share sebelum dihapus"]
HATE_KEYWORDS = ["kafir","munafik","pengkhianat bangsa","usir","bunuh","habisi","ganyang",
    "sampah masyarakat","parasit","perang saudara","revolusi berdarah"]
PROVOKASI_KEYWORDS = ["bangkit","lawan rezim","turunkan","gulingkan","people power",
    "massa turun","demo besar","ultimatum","rakyat marah","habis kesabaran"]
INCIDENT_KEYWORDS = {
    "BENCANA":  ["gempa","banjir","longsor","tsunami","erupsi","kebakaran hutan","bencana","korban",
                 "evakuasi","earthquake","flood","landslide","disaster","eruption"],
    "KONFLIK":  ["bentrokan","tawuran","kerusuhan","konflik","demonstrasi","unjuk rasa","ricuh",
                 "riot","clash","protest","unrest","violence"],
    "KRIMINAL": ["pembunuhan","pencurian","perampokan","penipuan","korupsi","narkoba",
                 "penangkapan","tersangka","murder","robbery","fraud","corruption","arrested"],
    "POLITIK":  ["pilkada","pemilu","pilpres","gubernur","bupati","politik","partai","kampanye",
                 "election","political","parliament"],
    "EKONOMI":  ["PHK","inflasi","harga naik","kemiskinan","pengangguran","investasi","rupiah",
                 "ekonomi","layoff","inflation","poverty","economy"],
    "KESEHATAN":["wabah","penyakit","virus","pandemi","rumah sakit","pasien","vaksin",
                 "outbreak","disease","epidemic","hospital"],
}
PROVINCES = {
    "Aceh":{"lat":4.6951,"lon":96.7494},"Sumatera Utara":{"lat":2.1154,"lon":99.5451},
    "Sumatera Barat":{"lat":-0.7399,"lon":100.8000},"Riau":{"lat":0.2933,"lon":101.7068},
    "Kepulauan Riau":{"lat":3.9456,"lon":108.1429},"Jambi":{"lat":-1.6101,"lon":103.6131},
    "Sumatera Selatan":{"lat":-3.3194,"lon":103.9144},"Bengkulu":{"lat":-3.7928,"lon":102.2608},
    "Lampung":{"lat":-4.5586,"lon":105.4068},"Kepulauan Bangka Belitung":{"lat":-2.7411,"lon":106.4406},
    "DKI Jakarta":{"lat":-6.2088,"lon":106.8456},"Jawa Barat":{"lat":-6.9175,"lon":107.6191},
    "Banten":{"lat":-6.4058,"lon":106.0640},"Jawa Tengah":{"lat":-7.1500,"lon":110.1403},
    "DI Yogyakarta":{"lat":-7.7956,"lon":110.3695},"Jawa Timur":{"lat":-7.5361,"lon":112.2384},
    "Bali":{"lat":-8.3405,"lon":115.0920},"Nusa Tenggara Barat":{"lat":-8.6529,"lon":117.3616},
    "Nusa Tenggara Timur":{"lat":-8.6574,"lon":121.0794},"Kalimantan Barat":{"lat":0.0000,"lon":109.3333},
    "Kalimantan Tengah":{"lat":-1.6815,"lon":113.3824},"Kalimantan Selatan":{"lat":-3.0926,"lon":115.2838},
    "Kalimantan Timur":{"lat":1.6407,"lon":116.4194},"Kalimantan Utara":{"lat":3.0731,"lon":116.0413},
    "Sulawesi Utara":{"lat":1.4931,"lon":124.8413},"Gorontalo":{"lat":0.5435,"lon":123.0568},
    "Sulawesi Tengah":{"lat":-1.4300,"lon":121.4456},"Sulawesi Barat":{"lat":-2.8442,"lon":119.2321},
    "Sulawesi Selatan":{"lat":-3.6688,"lon":119.9740},"Sulawesi Tenggara":{"lat":-4.1449,"lon":122.1746},
    "Maluku":{"lat":-3.2385,"lon":130.1453},"Maluku Utara":{"lat":1.5709,"lon":127.8088},
    "Papua Barat":{"lat":-1.3361,"lon":133.1747},"Papua":{"lat":-4.2699,"lon":138.0804},
}
CITIES = {
    "Jakarta":{"lat":-6.2088,"lon":106.8456,"province":"DKI Jakarta"},
    "Bandung":{"lat":-6.9175,"lon":107.6191,"province":"Jawa Barat"},
    "Surabaya":{"lat":-7.2575,"lon":112.7521,"province":"Jawa Timur"},
    "Semarang":{"lat":-6.9932,"lon":110.4203,"province":"Jawa Tengah"},
    "Yogyakarta":{"lat":-7.7956,"lon":110.3695,"province":"DI Yogyakarta"},
    "Malang":{"lat":-7.9666,"lon":112.6326,"province":"Jawa Timur"},
    "Bogor":{"lat":-6.5971,"lon":106.8060,"province":"Jawa Barat"},
    "Bekasi":{"lat":-6.2383,"lon":106.9756,"province":"Jawa Barat"},
    "Tangerang":{"lat":-6.1783,"lon":106.6319,"province":"Banten"},
    "Depok":{"lat":-6.4025,"lon":106.7942,"province":"Jawa Barat"},
    "Solo":{"lat":-7.5755,"lon":110.8243,"province":"Jawa Tengah"},
    "Medan":{"lat":3.5952,"lon":98.6722,"province":"Sumatera Utara"},
    "Palembang":{"lat":-2.9761,"lon":104.7754,"province":"Sumatera Selatan"},
    "Pekanbaru":{"lat":0.5335,"lon":101.4474,"province":"Riau"},
    "Batam":{"lat":1.0456,"lon":104.0305,"province":"Kepulauan Riau"},
    "Padang":{"lat":-0.9492,"lon":100.3543,"province":"Sumatera Barat"},
    "Banda Aceh":{"lat":5.5483,"lon":95.3238,"province":"Aceh"},
    "Pontianak":{"lat":-0.0263,"lon":109.3425,"province":"Kalimantan Barat"},
    "Samarinda":{"lat":-0.5022,"lon":117.1536,"province":"Kalimantan Timur"},
    "Balikpapan":{"lat":-1.2379,"lon":116.8529,"province":"Kalimantan Timur"},
    "Banjarmasin":{"lat":-3.3186,"lon":114.5944,"province":"Kalimantan Selatan"},
    "Makassar":{"lat":-5.1477,"lon":119.4327,"province":"Sulawesi Selatan"},
    "Manado":{"lat":1.4748,"lon":124.8421,"province":"Sulawesi Utara"},
    "Palu":{"lat":-0.9003,"lon":119.8779,"province":"Sulawesi Tengah"},
    "Denpasar":{"lat":-8.6705,"lon":115.2126,"province":"Bali"},
    "Mataram":{"lat":-8.5833,"lon":116.1167,"province":"Nusa Tenggara Barat"},
    "Kupang":{"lat":-10.1772,"lon":123.6070,"province":"Nusa Tenggara Timur"},
    "Ambon":{"lat":-3.6954,"lon":128.1814,"province":"Maluku"},
    "Jayapura":{"lat":-2.5337,"lon":140.7181,"province":"Papua"},
}
LOCATION_ALIASES = {
    "jakarta":"Jakarta","ibu kota":"Jakarta","dki":"Jakarta",
    "indonesia":"Jakarta","indonesian":"Jakarta",
    "west java":"Jawa Barat","east java":"Jawa Timur","central java":"Jawa Tengah",
    "yogyakarta":"DI Yogyakarta","jogja":"DI Yogyakarta","yogya":"DI Yogyakarta",
    "north sumatra":"Sumatera Utara","west sumatra":"Sumatera Barat",
    "south sumatra":"Sumatera Selatan","sumatra":"Sumatera Utara","sumatera":"Sumatera Utara",
    "north sulawesi":"Sulawesi Utara","south sulawesi":"Sulawesi Selatan",
    "sulawesi":"Sulawesi Selatan","west kalimantan":"Kalimantan Barat",
    "east kalimantan":"Kalimantan Timur","kalimantan":"Kalimantan Timur","borneo":"Kalimantan Timur",
    "west papua":"Papua Barat","papua":"Papua",
    "jabar":"Jawa Barat","jateng":"Jawa Tengah","jatim":"Jawa Timur",
    "sumut":"Sumatera Utara","sumsel":"Sumatera Selatan","sumbar":"Sumatera Barat",
    "sulsel":"Sulawesi Selatan","sulteng":"Sulawesi Tengah","sulut":"Sulawesi Utara",
    "kalbar":"Kalimantan Barat","kaltim":"Kalimantan Timur",
    "ntb":"Nusa Tenggara Barat","ntt":"Nusa Tenggara Timur",
    "aceh":"Aceh","bali":"Bali","riau":"Riau","bandung":"Bandung","bekasi":"Bekasi","bogor":"Bogor",
}
KNOWN_PERSONS = {
    "Elon Musk","Sam Altman","Jeff Bezos","Sundar Pichai","Tim Cook","Mark Zuckerberg",
    "Satya Nadella","Prabowo Subianto","Prabowo","Joko Widodo","Jokowi","Gibran",
    "Sri Mulyani","Anies Baswedan","Megawati","Airlangga","Luhut","Nadiem Makarim",
    "Donald Trump","Joe Biden","Kamala Harris","Barack Obama","Keir Starmer",
    "Emmanuel Macron","Vladimir Putin","Xi Jinping","Narendra Modi",
}
KNOWN_ORGS = {
    "Tesla","SpaceX","X Corp","OpenAI","Google","Apple","Microsoft","Amazon","Meta",
    "DOGE","SEC","NASA","UN","WHO","NATO","EU","IMF","Pertamina","PLN","Telkom",
    "BRI","BNI","Mandiri","TNI","Polri","KPK","DPR","MPR","MK","BI","OJK",
    "White House","Pentagon","Congress","Senate","BBC","CNN","Reuters","Bloomberg",
}
KNOWN_LOCS = {
    "United States","US","USA","Russia","China","Ukraine","Iran","Israel",
    "Europe","UK","Germany","France","Japan","India","Indonesia","Singapore",
    "Malaysia","Australia","Saudi Arabia","Middle East","Washington","New York",
    "London","Beijing","Moscow","Tehran","Gaza","Taiwan",
}
FALSE_POSITIVES = {
    "former google","education ministry","the indonesian","the white",
    "the court","this week","he said","she said","the senate",
}
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
#MainMenu,footer{visibility:hidden;}
.block-container{padding-top:1rem;padding-bottom:1rem;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:#0A0F1E;}
::-webkit-scrollbar-thumb{background:#1E3A5F;border-radius:4px;}
.stTabs [data-baseweb="tab-list"]{background:transparent;border-bottom:1px solid #1E3A5F;gap:4px;}
.stTabs [data-baseweb="tab"]{font-family:'DM Mono',monospace;font-size:.75rem;
  letter-spacing:.08em;padding:8px 16px;border-radius:6px 6px 0 0;
  color:rgba(255,255,255,.4)!important;background:transparent;border:none;}
.stTabs [aria-selected="true"]{background:rgba(79,195,247,.1)!important;
  color:#4FC3F7!important;border-bottom:2px solid #4FC3F7!important;}
div[data-testid="stButton"] button{
  background:rgba(79,195,247,.1)!important;color:#4FC3F7!important;
  border:1px solid rgba(79,195,247,.3)!important;border-radius:6px!important;
  font-family:'DM Mono',monospace!important;font-size:.78rem!important;}
div[data-testid="stButton"] button:hover{background:rgba(79,195,247,.2)!important;}
section[data-testid="stSidebar"]{background:#050A14;}
section[data-testid="stSidebar"] *{color:rgba(255,255,255,.8)!important;}
section[data-testid="stSidebar"] hr{border-color:#1E3A5F!important;}
</style>
"""
