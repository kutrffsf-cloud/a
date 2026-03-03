from flask import Flask, request, render_template_string, send_file, jsonify
import io
from datetime import datetime

app = Flask(__name__)

# ===== KONFIGURACJA =====
MAX_FILES_PER_ROOM = 20       # Maksymalna liczba plików w pokoju
MAX_FILE_SIZE_MB = 5          # Maksymalny rozmiar pojedynczego pliku w MB
ROOM_CODE_LENGTH = 4

# ===== PAMIĘĆ NA POKOJE I PLIKI =====
# Struktura: { "1234": [{"name": "plik.txt", "data": b"...", "timestamp": datetime} ] }
rooms = {}

# ===== FRONTEND =====
HTML_PAGE = """
<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Piotrczat</title>
<style>
body { font-family: Arial; background: #f0f0f0; padding: 20px; }
h1 { color: #333; }
input, button { padding: 10px; margin: 5px; font-size: 16px; }
#files { margin-top: 20px; }
.file-item { margin: 5px 0; display:block; }
.room-container { background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px #ccc; margin-top: 20px; }
</style>
</head>
<body>
<h1>Piotrczat 🌐</h1>

<div class="room-container">
    <h3>Dołącz / Stwórz pokój</h3>
    <input type="text" id="room_code" placeholder="4-cyfrowy kod" maxlength="4">
    <button onclick="joinRoom()">Dołącz / Stwórz</button>
</div>

<div class="room-container" id="room_section" style="display:none;">
    <h3>Pokój: <span id="current_room"></span></h3>
    <input type="file" id="file_input">
    <button onclick="uploadFile()">Wyślij plik</button>
    <div id="files"></div>
</div>

<script>
let currentRoom = null;

function joinRoom(){
    let code = document.getElementById("room_code").value;
    if(!code || code.length != 4){ alert("Wpisz 4-cyfrowy kod"); return; }
    fetch("/join?code="+code).then(r=>r.json()).then(data=>{
        if(data.error){ alert(data.error); return; }
        currentRoom = code;
        document.getElementById("current_room").innerText = currentRoom;
        document.getElementById("room_section").style.display="block";
        refreshFiles();
    });
}

function uploadFile(){
    let fileInput = document.getElementById("file_input");
    if(fileInput.files.length==0){ alert("Wybierz plik"); return; }
    let file = fileInput.files[0];
    if(file.size > {{max_file_size}}*1024*1024){
        alert("Plik za duży, max {{max_file_size}} MB");
        return;
    }
    let formData = new FormData();
    formData.append("file", file);
    formData.append("room_code", currentRoom);
    fetch("/upload", {method:"POST", body: formData}).then(r=>r.json()).then(data=>{
        if(data.error){ alert(data.error); return; }
        refreshFiles();
    });
}

function refreshFiles(){
    fetch("/files?code="+currentRoom).then(r=>r.json()).then(data=>{
        let div = document.getElementById("files");
        div.innerHTML = "";
        data.files.forEach(f=>{
            let link = document.createElement("a");
            link.href="/download?room="+currentRoom+"&name="+encodeURIComponent(f);
            link.innerText=f;
            link.className="file-item";
            div.appendChild(link);
        });
    });
}
</script>
</body>
</html>
"""

# ===== ROUTING =====
@app.route("/")
def home():
    return render_template_string(HTML_PAGE, max_file_size=MAX_FILE_SIZE_MB)

@app.route("/join")
def join_room():
    code = request.args.get("code")
    if not code or len(code)!=ROOM_CODE_LENGTH:
        return jsonify({"error":"Niepoprawny kod"}), 400
    if code not in rooms:
        rooms[code] = []
    return jsonify({"ok": True})

@app.route("/upload", methods=["POST"])
def upload_file():
    code = request.form.get("room_code")
    if not code or code not in rooms:
        return jsonify({"error":"Pokój nie istnieje"}), 400
    file = request.files.get("file")
    if not file:
        return jsonify({"error":"Brak pliku"}), 400
    if len(file.read()) > MAX_FILE_SIZE_MB*1024*1024:
        return jsonify({"error": f"Plik za duży, max {MAX_FILE_SIZE_MB} MB"}), 400
    file.seek(0)  # wracamy na początek pliku
    data = file.read()
    rooms[code].append({"name": file.filename, "data": data, "timestamp": datetime.now()})
    
    # ===== AUTOMATYCZNE CZYSZCZENIE STARYCH PLIKÓW =====
    if len(rooms[code]) > MAX_FILES_PER_ROOM:
        rooms[code] = rooms[code][-MAX_FILES_PER_ROOM:]
    
    return jsonify({"ok": True})

@app.route("/files")
def list_files():
    code = request.args.get("code")
    if not code or code not in rooms:
        return jsonify({"files":[]})
    files = [f["name"] for f in rooms[code]]
    return jsonify({"files": files})

@app.route("/download")
def download_file():
    code = request.args.get("room")
    name = request.args.get("name")
    if not code or code not in rooms:
        return "Pokój nie istnieje", 400
    for f in rooms[code]:
        if f["name"]==name:
            return send_file(io.BytesIO(f["data"]), download_name=name, as_attachment=True)
    return "Plik nie istnieje", 404

# ===== URUCHOMIENIE =====
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
