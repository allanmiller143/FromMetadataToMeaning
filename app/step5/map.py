from collections import defaultdict, Counter
import json

from matplotlib import cm
import numpy as np


def build_interactive_map_v3(som, themes, embeddings, macrothemes, occurrences, tables_by_theme, out_path, umatrix, metadata_dict=None):
    """
    Gera um HTML interativo com D3.js para explorar o SOM.
    Inclui U-Matrix, Macrotemas, Temas e Tabelas de Origem.
    """
    weights = som.get_weights()
    x_dim, y_dim = weights.shape[0], weights.shape[1]
    
    neuron_data = defaultdict(list)
    theme_to_macro = {}
    for m in macrothemes:
        for t in m["subtemas"]:
            theme_to_macro[t] = m

    for i, t in enumerate(themes):
        w = som.winner(embeddings[i])
        neuron_data[w].append({
            "theme": t,
            "freq": int(occurrences[t]),
            "tables": sorted(list(tables_by_theme.get(t, [])))
        })

    # Preparar dados para o D3
    grid_data = []
    colors = ["#01696f","#EF553B","#AB63FA","#FFA15A","#19D3F3","#FF6692","#B6E880","#FF97FF","#FECB52","#636EFA","#7FDBFF","#2ECC40","#FFDC00","#FF851B","#85144b","#3D9970","#a29bfe","#fd79a8","#00b894","#e17055"]
    macro_to_color = {m["macrotema"]: colors[i % len(colors)] for i, m in enumerate(macrothemes)}

    for x in range(x_dim):
        for y in range(y_dim):
            themes_in_neuron = neuron_data.get((x, y), [])
            themes_in_neuron.sort(key=lambda x: x["freq"], reverse=True)
            
            macro = None
            if themes_in_neuron:
                rep_theme = themes_in_neuron[0]["theme"]
                macro = theme_to_macro.get(rep_theme)
            
            color = macro_to_color.get(macro["macrotema"], "#333") if macro else "#1a1a1a"
            
            grid_data.append({
                "id": f"{x}_{y}",
                "x": x,
                "y": y,
                "u_val": float(umatrix[x, y]),
                "color": color,
                "count": len(themes_in_neuron),
                "themes": themes_in_neuron,
                "macro": macro['macrotema'] if macro else None
            })

    data_json = json.dumps(grid_data, ensure_ascii=False)
    macros_ordered = sorted(macrothemes, key=lambda x: x["frequencia_total"], reverse=True)
    macros_json = json.dumps([m['macrotema'] for m in macros_ordered[:20]], ensure_ascii=False)
    metadata_json = json.dumps(metadata_dict or {}, ensure_ascii=False, default=str)

    # Preparar dados de U-Matrix normalizada para colormap inferno
    umatrix_min = float(np.min(umatrix))
    umatrix_max = float(np.max(umatrix))
    umatrix_range = umatrix_max - umatrix_min if umatrix_max > umatrix_min else 1.0
    
    # Criar mapa de cores inferno normalizado
    cmap_inferno = cm.get_cmap('inferno')
    umatrix_colors = {}
    for x in range(x_dim):
        for y in range(y_dim):
            normalized_val = (float(umatrix[x, y]) - umatrix_min) / umatrix_range
            rgba = cmap_inferno(normalized_val)
            hex_color = '#{:02x}{:02x}{:02x}'.format(int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))
            umatrix_colors[f"{x}_{y}"] = hex_color
    
    umatrix_colors_json = json.dumps(umatrix_colors, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Mapa Hexbin — Temas do SOM</title>
    <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
    <style>
        :root {{
            --bg: #121212; --surface: #1e1e1e; --text: #e0e0e0; --text-muted: #a0a0a0;
            --primary: #ff9f43; --border: #333; --sidebar-bg: #181818;
            --accent: #ff9f43;
        }}
        [data-theme="light"] {{
            --bg: #f5f5f5; --surface: #ffffff; --text: #222222; --text-muted: #666666;
            --primary: #e67e22; --border: #ddd; --sidebar-bg: #fdfdfd;
            --accent: #ff9f43;
        }}
        body {{ margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); overflow: hidden; }}
        #app {{ width: 100vw; height: 100vh; display: flex; flex-direction: column; }}
        
        header {{ display: flex; justify-content: space-between; align-items: flex-start; padding: 30px 20px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }}
        .title-area h1 {{ margin: 0; font-size: 1.3rem; font-weight: 700; }}
        .title-area p {{ margin: 3px 0 0; color: var(--text-muted); font-size: 0.85rem; }}
        
        .controls-top {{ display: flex; align-items: center; gap: 20px; padding: 12px 20px; background: var(--surface); border-bottom: 1px solid var(--border); flex-shrink: 0; }}
        .control-group {{ display: flex; align-items: center; gap: 10px; font-size: 0.8rem; }}
        input[type="text"] {{ background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 5px 12px; border-radius: 20px; outline: none; width: 180px; font-size: 0.8rem; }}
        
        .main-content {{ display: flex; flex: 1; overflow: hidden; position: relative; }}
        
        #viz-container {{ flex: 1; background: var(--bg); position: relative; overflow: hidden; }}
        svg {{ width: 100%; height: 100%; cursor: default; }}
        
        #sidebar {{
            width: 320px; background: var(--sidebar-bg); border-left: 1px solid var(--border);
            display: flex; flex-direction: column; transition: transform 0.3s ease;
            position: relative; z-index: 100; flex-shrink: 0;
        }}
        .sidebar-header {{ padding: 20px; border-bottom: 1px solid var(--border); }}
        .sidebar-header h2 {{ margin: 0; font-size: 1.1rem; color: var(--primary); }}
        .sidebar-empty {{ display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); text-align: center; padding: 20px; font-style: italic; }}
        .theme-list-item {{ margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
        .theme-list-item:last-child {{ border-bottom: none; }}
        .theme-freq {{ color: var(--primary); font-weight: bold; font-size: 0.75rem; }}

        .hexagon {{ stroke: var(--bg); stroke-width: 0.5px; transition: filter 0.2s; cursor: pointer; pointer-events: all; }}
        .hexagon:hover {{ filter: brightness(5); }}
        .hexagon.highlight {{ filter: brightness(5); }}
        .hexagon.dimmed {{ opacity: 0.1; }}
        .hexagon.empty {{ stroke: var(--border); stroke-dasharray: 2,2; pointer-events: none; }}
        .hexagon.selected {{ filter: brightness(50) !important; stroke: var(--primary) !important; stroke-width: 2px !important; }}

        .axis-label {{ font-size: 10px; fill: var(--text-muted); pointer-events: none; }}
        .grid-line {{ stroke: var(--border); stroke-dasharray: 2,2; stroke-width: 0.5; pointer-events: none; }}
        
        #tooltip {{
            position: fixed; pointer-events: none; background: rgba(0,0,0,0.95);
            border: 1px solid #555; padding: 12px; border-radius: 8px; font-size: 0.8rem;
            display: none; box-shadow: 0 8px 20px rgba(0,0,0,0.7); z-index: 2000; color: #fff;
            max-height: 400px; overflow-y: auto; max-width: 300px;
        }}
        
        .t-macro {{ color: var(--primary); font-weight: bold; display: block; margin-bottom: 5px; border-bottom: 1px solid #444; padding-bottom: 4px; }}
        
        #legend {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 20px; background: var(--surface); border-top: 1px solid var(--border); justify-content: flex-start; overflow-y: auto; flex-shrink: 0; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.7rem; color: var(--text-muted); background: var(--bg); padding: 5px 10px; border-radius: 20px; border: 1px solid var(--border); cursor: pointer; transition: all 0.2s; white-space: nowrap; }}
        .legend-item:hover {{ border-color: var(--primary); color: var(--text); }}
        .legend-item.active {{ background: var(--primary); color: #000; border-color: var(--primary); }}
        .legend-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
        .legend-section-title {{ width: 100%; font-size: 0.7rem; font-weight: 600; color: var(--text-muted); padding: 5px 0; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        .stats-panel {{ position: absolute; top: 10px; right: 10px; background: var(--surface); border: 1px solid var(--border); padding: 10px; border-radius: 8px; font-size: 0.75rem; z-index: 10; pointer-events: none; }}
        .stat-item {{ margin-bottom: 4px; }}
        .stat-value {{ font-weight: bold; color: var(--primary); }}
        .export-btn {{ background: var(--primary); color: #000; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 0.75rem; margin-left: auto; }}
        .export-btn:hover {{ opacity: 0.9; }}
        .sidebar-search {{ padding: 10px 20px; border-bottom: 1px solid var(--border); }}
        .sidebar-search input {{ width: 100%; box-sizing: border-box; }}
        
        /* RESTAURAÇÃO DAS TAGS DE TABELA ORIGINAIS COM ESTADO SALVO */
        .table-tag {{ 
            display: inline-block; background: var(--border); color: var(--text-muted); 
            font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; margin: 2px; 
            cursor: pointer; transition: all 0.2s; 
        }}
        .table-tag:hover {{ background: var(--primary); color: #000; }}
        .table-tag.saved {{ background: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }}
        .table-tag.saved:hover {{ background: #2ecc71; color: #000; }}
        
        /* MODAL STYLES */
        .modal-overlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.7); z-index: 3000; align-items: center; justify-content: center;
            padding: 20px;
        }}
        .modal-overlay.active {{ display: flex; }}
        
        .modal-content {{
            background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
            max-width: 1100px; width: 95%; max-height: 88vh; overflow: hidden;
            padding: 0; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9);
            display: flex; flex-direction: column;
        }}
        
        .modal-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 0; border-bottom: 1px solid var(--border); padding: 18px 22px;
            flex-shrink: 0; background: var(--surface);
        }}
        
        .modal-header h2 {{
            margin: 0; font-size: 1.3rem; color: var(--text); word-break: break-word;
            padding-right: 10px;
        }}
        
        .modal-close {{
            background: none; border: none; color: var(--text); font-size: 1.5rem;
            cursor: pointer; padding: 0; width: 30px; height: 30px; display: flex;
            align-items: center; justify-content: center; transition: color 0.2s;
            flex-shrink: 0;
        }}
        
        .modal-close:hover {{ color: var(--primary); }}
        
        .modal-body {{
            padding: 22px; overflow-y: auto; flex: 1;
        }}
        
        .modal-section {{ margin-bottom: 25px; }}
        .modal-section h3 {{ margin: 0 0 12px; font-size: 0.95rem; color: var(--text); }}
        
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }}
        .info-item {{ background: var(--bg); padding: 12px; border-radius: 8px; border: 1px solid var(--border); }}
        .info-label {{ font-size: 0.7rem; color: var(--text-muted); margin-bottom: 4px; }}
        .info-value {{ font-size: 0.9rem; font-weight: 600; }}
        
        .table-wrapper {{ overflow-x: auto; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); }}
        .columns-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        .columns-table th {{ text-align: left; padding: 12px; background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border); color: var(--text-muted); font-weight: 600; }}
        .columns-table td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
        .columns-table tr:last-child td {{ border-bottom: none; }}
        
        .add-finding-btn {{
            background: var(--primary); color: #000; border: none; padding: 10px 20px;
            border-radius: 6px; cursor: pointer; font-weight: 700; font-size: 0.85rem;
            transition: all 0.2s; margin-top: 15px; display: inline-flex; align-items: center; gap: 8px;
        }}
        .add-finding-btn:hover {{ opacity: 0.9; transform: translateY(-1px); }}
        .add-finding-btn:active {{ transform: translateY(0); }}
        .add-finding-btn:disabled {{ background: #2ecc71; color: #fff; cursor: default; opacity: 1; }}

        /* FINDINGS PANEL */
        #findings-panel {{
            width: 300px; background: var(--sidebar-bg); border-left: 1px solid var(--border);
            display: flex; flex-direction: column; transition: transform 0.3s ease;
            position: relative; z-index: 100; flex-shrink: 0;
        }}
        .findings-header {{ padding: 10px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-direction: column; gap:5px; }}
        .findings-header h2 {{ margin: 0; font-size: 1.1rem; color: var(--primary); }}
        .findings-list {{ flex: 1; overflow-y: auto; padding: 15px; }}
        .finding-item {{
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 12px; margin-bottom: 12px; position: relative;
            transition: border-color 0.2s;
            cursor: pointer;
        }}
        .finding-item:hover {{ border-color: var(--primary); }}
        .finding-type {{ font-size: 0.6rem; text-transform: uppercase; color: var(--primary); font-weight: bold; display: block; margin-bottom: 4px; }}
        .finding-title {{ font-size: 0.85rem; font-weight: 600; display: block; margin-bottom: 6px; word-break: break-all; }}
        .remove-btn {{
            position: absolute; top: 8px; right: 8px; background: none; border: none;
            color: var(--text-muted); cursor: pointer; font-size: 1.1rem; padding: 0;
            line-height: 1;
        }}
        .remove-btn:hover {{ color: #ff4757; }}
        .findings-footer {{ padding: 10px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; }}
        .export-findings-btn {{
            background: var(--bg); color: var(--text); border: 1px solid var(--border);
            padding: 8px; border-radius: 4px; cursor: pointer; font-size: 0.75rem;
            transition: all 0.2s; font-weight: 600;
        }}
        .export-findings-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
        .export-findings-btn.primary {{ background: var(--primary); color: #000; border: none; }}
        .export-findings-btn.primary:hover {{ opacity: 0.9; color: #000; }}
        .finding-status {{ font-size: 0.65rem; color: #2ecc71; font-weight: bold; margin-top: 5px; display: block; }}

        #findings-trigger {{
            position: fixed; bottom: 20px; right: 340px; z-index: 500;
            background: var(--primary); color: #000; width: 50px; height: 50px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            transition: transform 0.2s;
        }}
        #findings-trigger:hover {{ transform: scale(1.1); }}
    </style>
</head>
<body>
    <div id="app">        
        <div class="controls-top">
            <div class="control-group">
                <label>Macrotema:</label>
                <input type="text" id="search-macro" placeholder="Filtrar macrotema...">
            </div>
            <div class="control-group">
                <label>Tema:</label>
                <input type="text" id="search-theme" placeholder="Buscar tema...">
            </div>
            <div style="margin-left: auto; display: flex; gap: 10px;">
                <button class="export-btn" onclick="toggleFindings()">Meus Achados (<span id="findings-count">0</span>)</button>
            </div>
        </div>

        <div class="main-content">
            <div id="viz-container">
                <svg id="viz"></svg>
                <div class="stats-panel">
                    <div class="stat-item">Total de Temas: <span id="stat-total-themes" class="stat-value">0</span></div>
                    <div class="stat-item">Neurônios Ativos: <span id="stat-active-neurons" class="stat-value">0</span></div>
                    <div class="stat-item">Densidade Média: <span id="stat-avg-density" class="stat-value">0</span></div>
                </div>
            </div>
            
            <div id="sidebar">
                <div class="sidebar-empty">Clique em um hexágono para ver os temas</div>
            </div>
            
            <div id="tooltip"></div>
            
            <!-- PAINEL DE ACHADOS -->
            <div id="findings-panel" style="display: none;">
                <div class="findings-header">
                    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                        <h2>Meus Achados</h2>
                        <button class="modal-close" onclick="toggleFindings()">&times;</button>
                    </div>
                    <input type="text" id="download-filename" placeholder="Título do arquivo" style="width: 100%; box-sizing: border-box; padding: 8px; border-radius: 4px; background: var(--bg); border: 1px solid var(--border); color: var(--text); font-size: 0.8rem;">
                </div>
                <div id="findings-list" class="findings-list">
                    <div style="text-align: center; color: var(--text-muted); padding: 40px 0; font-style: italic; font-size: 0.8rem;">
                        Nenhum achado salvo ainda.<br>Clique em "Salvar" nas tabelas.
                    </div>
                </div>
                <div class="findings-footer">
                    <button class="export-findings-btn primary" onclick="exportFindings('md')">Exportar Relatório (MD)</button>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                        <button class="export-findings-btn" onclick="exportFindings('csv')">CSV</button>
                        <button class="export-findings-btn" onclick="exportFindings('json')">JSON</button>
                    </div>
                </div>
            </div>
        </div>

        <div id="legend"></div>
    </div>

    <!-- MODAL PARA DETALHES DE TABELA -->
    <div id="modal-overlay" class="modal-overlay">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-table-name">Nome da Tabela</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <button id="add-table-finding-btn" class="add-finding-btn" style="margin-top: 0; padding: 6px 12px;">Salvar Tabela</button>
                    <button class="modal-close" onclick="closeTableModal()">&times;</button>
                </div>
            </div>
            <div id="modal-body" class="modal-body"></div>
        </div>
    </div>

    <script>
        const data = {data_json};
        const macros = {macros_json};
        const metadataDict = {metadata_json};
        const umatrixColors = {umatrix_colors_json};
        const svg = d3.select("#viz");
        const g = svg.append("g");
        const tooltip = d3.select("#tooltip");
        const sidebar = d3.select("#sidebar");

        let macroQuery = "";
        let themeQuery = "";
        let sidebarFilter = "";
        let activeMacro = null;
        let selectedNeuronId = null;
        let findings = JSON.parse(localStorage.getItem('som_findings') || '[]');
        let savedTableNames = new Set(findings.map(f => f.title));

        const xExtent = d3.extent(data, d => d.x);
        const yExtent = d3.extent(data, d => d.y);
        const xRange = xExtent[1] - xExtent[0];
        const maxY = yExtent[1];
        const yRange = maxY - yExtent[0];

        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});

        svg.call(zoom);

        function getHexPath(radius) {{
            const points = [];
            for (let i = 0; i < 6; i++) {{
                const angle = (Math.PI / 3) * i - (Math.PI / 6);
                points.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
            }}
            return "M" + points.join("L") + "Z";
        }}

        function updateSidebar(d) {{
            if (!d || d.count === 0) {{
                sidebar.html('<div class="sidebar-empty">Clique em um hexágono para fixar a visualização lateral</div>');
                return;
            }}
            
            const tQ = themeQuery.toLowerCase().trim();
            const sF = sidebarFilter.toLowerCase().trim();
            
            const filteredThemes = d.themes.filter(t => 
                (sF === "" || t.theme.toLowerCase().includes(sF))
            );

            let html = `
                <div class="sidebar-header">
                    <div>
                        <h2 style="flex: 1;">${{d.macro || "Sem Macrotema"}}</h2>
                    </div>
                    <div class="neuron-info">Neurônio (${{d.x}}, ${{d.y}}) — ${{d.count}} temas</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 5px;">Distância U-Matrix: ${{d.u_val.toFixed(4)}}</div>
                </div>
                <div class="sidebar-search">
                    <input type="text" id="sidebar-filter-input" placeholder="Filtrar nesta lista..." value="${{sidebarFilter}}" 
                        oninput="sidebarFilter = this.value; updateSidebar(data.find(n => n.id === '${{d.id}}'))">
                </div>
                <div class="sidebar-content" style="flex: 1; overflow-y: auto; padding: 0 20px 20px;">
                    <div style="font-weight: bold; margin: 15px 0 10px; border-bottom: 1px solid var(--border); padding-bottom: 5px; font-size: 0.9rem; position: sticky; top: 0; background: var(--sidebar-bg); z-index: 1;">
                        Temas e Tabelas (${{filteredThemes.length}}):
                    </div>
            `;
            
            html += filteredThemes.map(t => {{
                const match = tQ !== "" && t.theme.toLowerCase().includes(tQ);
                const highlightStyle = match ? 'style="background: rgba(255, 159, 67, 0.15); border-left: 3px solid var(--primary); padding-left: 8px;"' : 'style="padding-left: 8px;"';
                
                const tablesHtml = t.tables && t.tables.length > 0 
                    ? `<div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px;">
                         ${{t.tables.map(tab => {{
                             const isSaved = savedTableNames.has(tab);
                             const savedClass = isSaved ? 'saved' : '';
                             const savedIcon = isSaved ? '✓ ' : '';
                             return `<span class="table-tag ${{savedClass}}" onclick="openTableModal('${{tab}}')">${{savedIcon}}${{tab}}</span>`;
                         }}).join("")}}
                       </div>`
                    : "";

                return `
                    <div class="theme-list-item" ${{highlightStyle}}>
                        <div>
                            <span style="font-weight: 600; font-size: 0.85rem;">${{t.theme}}</span>
                            <span class="theme-freq" title="Frequência">(${{t.freq}})</span>
                        </div>
                        ${{tablesHtml}}
                    </div>
                `;
            }}).join("");
            
            if (filteredThemes.length === 0) {{
                html += `<div style="text-align: center; color: var(--text-muted); padding: 20px; font-style: italic;">Nenhum tema corresponde ao filtro.</div>`;
            }}

            html += `</div>`;
            sidebar.html(html);
            
            const input = document.getElementById('sidebar-filter-input');
            if (input) {{
                input.focus();
                input.setSelectionRange(input.value.length, input.value.length);
            }}
        }}

        function handleHexClick(event, d) {{
            if (event.button !== 0) return;
            if (d.count === 0) return;
            
            if (selectedNeuronId === d.id) {{
                selectedNeuronId = null;
                sidebarFilter = "";
                updateSidebar(null);
            }} else {{
                selectedNeuronId = d.id;
                sidebarFilter = "";
                updateSidebar(d);
            }}
            
            g.selectAll(".hexagon").classed("selected", d_hex => d_hex.id === selectedNeuronId);
            event.stopPropagation();
        }}

        function render() {{
            const currentTransform = d3.zoomTransform(svg.node());
            g.selectAll("*").remove();
            
            const containerWidth = document.getElementById("viz-container").clientWidth;
            const containerHeight = document.getElementById("viz-container").clientHeight;
            
            const hexW_target = (containerWidth * 0.85) / (xRange + 1);
            const hexH_target = (containerHeight * 0.85) / (yRange + 1);
            
            const radius = Math.min(hexW_target / Math.sqrt(3), hexH_target / 1.5);
            const hexW = Math.sqrt(3) * radius;
            const hexH = 2 * radius;
            const vertDist = (3/4) * hexH;
            const totalHeight = (yRange) * vertDist + hexH;
            
            const marginLeft = 60; 
            const marginTop = 70;
            
            const initialScale = 0.8;
            const transform = d3.zoomIdentity
                .translate(marginLeft, marginTop)
                .scale(initialScale);
            svg.call(zoom.transform, transform);

            for (let i = xExtent[0]; i <= xExtent[1]; i++) {{
                const px = (i - xExtent[0]) * hexW;
                g.append("line").attr("class", "grid-line").attr("x1", px).attr("y1", -20).attr("x2", px).attr("y2", totalHeight);
                g.append("text").attr("class", "axis-label").attr("x", px).attr("y", totalHeight + 20).attr("text-anchor", "middle").text(i);
            }}
            
            for (let i = yExtent[0]; i <= maxY; i++) {{
                const invertedY = maxY - i;
                const py = (invertedY - yExtent[0]) * vertDist;
                g.append("text").attr("class", "axis-label").attr("x", -30).attr("y", py + 4).attr("text-anchor", "end").text(i);
            }}

            const hexes = g.selectAll(".hexagon")
                .data(data)
                .enter()
                .append("path")
                .attr("class", d => {{
                    let classes = d.count > 0 ? "hexagon" : "hexagon empty";
                    if (selectedNeuronId === d.id) classes += " selected";
                    return classes;
                }})
                .attr("d", getHexPath(radius))
                .attr("transform", d => {{
                    const invertedY = maxY - d.y;
                    const px = (d.x - xExtent[0]) * hexW + (invertedY % 2 === 1 ? hexW / 2 : 0);
                    const py = (invertedY - yExtent[0]) * vertDist;
                    return `translate(${{px}}, ${{py}})`;
                }})
                .attr("fill", d => d.count > 0 ? (umatrixColors[d.id] || d.color) : "none")
                .on("mouseover", function(event, d) {{
                    if(d.count === 0) return;
                    d3.select(this).classed("highlight", true);
                    tooltip.style("display", "block");
                    updateTooltip(event, d);
                    if (selectedNeuronId === null) updateSidebar(d);
                }})
                .on("mousemove", (event) => {{
                    let x = event.clientX + 20;
                    let y = event.clientY + 20;
                    const tooltipWidth = 300;
                    const tooltipHeight = tooltip.node().offsetHeight || 200;
                    if (x + tooltipWidth > window.innerWidth) x = event.clientX - tooltipWidth - 20;
                    if (y + tooltipHeight > window.innerHeight) y = event.clientY - tooltipHeight - 20;
                    tooltip.style("left", x + "px").style("top", y + "px");
                }})
                .on("mouseout", function() {{
                    d3.select(this).classed("highlight", false);
                    tooltip.style("display", "none");
                    if (selectedNeuronId === null) updateSidebar(null);
                }})
                .on("click", handleHexClick);

            updateStats();
            applyFilters();
        }}

        function updateTooltip(event, d) {{
            let content = `<span class="t-macro">${{d.macro || "Sem Macrotema"}}</span>`;
            content += `<div style="margin-bottom:8px; font-size:0.7rem; color:#aaa;">Neurônio: (${{d.x}}, ${{d.y}}) | Temas: ${{d.count}}</div>`;
            const tQ = themeQuery.toLowerCase().trim();
            const visibleThemes = d.themes.slice(0, 10);
            content += visibleThemes.map(t => {{
                const match = tQ !== "" && t.theme.toLowerCase().includes(tQ);
                const style = match ? 'style="color:var(--primary); font-weight:bold;"' : '';
                return `<div ${{style}}>• ${{t.theme}} (${{t.freq}})</div>`;
            }}).join("");
            if(d.themes.length > 10) content += `<div style="color:var(--primary); margin-top:4px;">+ ${{d.themes.length - 10}} outros (veja na lateral)</div>`;
            tooltip.html(content);
        }}

        function applyFilters() {{
            const mQ = macroQuery.toLowerCase().trim();
            const tQ = themeQuery.toLowerCase().trim();
            g.selectAll(".hexagon:not(.empty)").each(function(d) {{
                const macroName = (d.macro || "").toLowerCase();
                const hasMacroMatch = mQ === "" || macroName.includes(mQ);
                const isMacroActive = !activeMacro || d.macro === activeMacro;
                const hasThemeMatch = tQ === "" || d.themes.some(t => t.theme.toLowerCase().includes(tQ));
                const isVisible = hasMacroMatch && isMacroActive && hasThemeMatch;
                const isSearching = mQ !== "" || tQ !== "" || activeMacro !== null;
                d3.select(this).classed("dimmed", isSearching && !isVisible).classed("highlight", isSearching && isVisible);
            }});
        }}

        function updateStats() {{
            const activeNeurons = data.filter(d => d.count > 0);
            const totalThemes = d3.sum(activeNeurons, d => d.count);
            const avgDensity = totalThemes / activeNeurons.length || 0;
            
            document.getElementById("stat-total-themes").innerText = totalThemes;
            document.getElementById("stat-active-neurons").innerText = activeNeurons.length;
            document.getElementById("stat-avg-density").innerText = avgDensity.toFixed(1);
        }}

        function buildLegend() {{
            const leg = d3.select("#legend");
            leg.selectAll("*").remove();
            leg.append("div").attr("class", "legend-section-title").text("Macrotemas (ordenados por frequência)");
            const colors = ["#01696f","#EF553B","#AB63FA","#FFA15A","#19D3F3","#FF6692","#B6E880","#FF97FF","#FECB52","#636EFA","#7FDBFF","#2ECC40","#FFDC00","#FF851B","#85144b","#3D9970","#a29bfe","#fd79a8","#00b894","#e17055"];
            macros.forEach((m, i) => {{
                const item = leg.append("div").attr("class", "legend-item")
                    .on("click", function() {{
                        const isActive = d3.select(this).classed("active");
                        leg.selectAll(".legend-item").classed("active", false);
                        if(!isActive) {{ d3.select(this).classed("active", true); activeMacro = m; }} else {{ activeMacro = null; }}
                        applyFilters();
                    }});
                item.append("div").attr("class", "legend-dot").style("background", colors[i % colors.length]);
                item.append("span").text(m);
            }});
        }}

        function toggleFindings() {{
            const panel = document.getElementById("findings-panel");
            const isVisible = panel.style.display !== "none";
            panel.style.display = isVisible ? "none" : "flex";
            if (!isVisible) updateFindingsList();
        }}

        function closeTableModal() {{
            document.getElementById("modal-overlay").classList.remove("active");
        }}

        // ===== FUNÇÕES DO MODAL - VERSÃO COM CONTEÚDO ENRIQUECIDO =====

        function openTableModal(tableName) {{
            const cleanTableName = tableName.includes('.') ? tableName.split('.')[1] : tableName;
            const tableData = metadataDict[cleanTableName];
            if (!tableData) {{
                alert(`Dados da tabela "${{tableName}}" não encontrados.`);
                return;
            }}

            document.getElementById("modal-table-name").textContent = tableName;
            
            const addBtn = document.getElementById("add-table-finding-btn");
            const isSaved = savedTableNames.has(tableName);
            
            if (isSaved) {{
                addBtn.innerText = "✓ Salvo";
                addBtn.style.background = "#2ecc71";
                addBtn.disabled = true;
            }} else {{
                addBtn.innerText = "Salvar Tabela";
                addBtn.style.background = "";
                addBtn.disabled = false;
                addBtn.onclick = (e) => addFinding('Tabela', tableName.replace(/'/g, "\\\\'"), `Linhas: ${{tableData.row_count || "N/A"}} | Colunas: ${{tableData.columns ? tableData.columns.length : "N/A"}}`, tableName, e);
            }}
            
            let modalBody = `
                <div class="modal-section">
                    <h3>Informações da Tabela</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Nome</div>
                            <div class="info-value">${{tableName}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Linhas</div>
                            <div class="info-value">${{tableData.row_count || "N/A"}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Colunas</div>
                            <div class="info-value">${{tableData.columns ? tableData.columns.length : "N/A"}}</div>
                        </div>
                    </div>
                </div>
            `;
            
            // Seção de Colunas
            if (tableData.columns && tableData.columns.length > 0) {{
                modalBody += `
                    <div class="modal-section">
                        <h3>Colunas (${{tableData.columns.length}})</h3>
                        <div class="table-wrapper">
                            <table class="columns-table">
                                <thead>
                                    <tr>
                                        <th>Nome</th>
                                        <th>Tipo</th>
                                        <th>Nullable</th>
                                        <th>Exemplos</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;

                tableData.columns.forEach(col => {{
                    const nullable = col.nullable ? "Sim" : "Não";
                    let examples = "";
                    
                    if (col.stats && col.stats.sample_values && col.stats.sample_values.length > 0) {{
                        examples = col.stats.sample_values
                            .slice(0, 3)
                            .map(v => v !== null && v !== undefined ? String(v) : "NULL")
                            .join(", ");
                        if (col.stats.sample_values.length > 3) {{
                            examples += "...";
                        }}
                    }}

                    modalBody += `
                        <tr>
                            <td><strong>${{col.name}}</strong></td>
                            <td>${{col.type || "—"}}</td>
                            <td>${{nullable}}</td>
                            <td title="${{examples || "—"}}"><span class="sample-values">${{examples || "—"}}</span></td>
                        </tr>
                    `;
                }});

                modalBody += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            }}

            // Seção de Estatísticas (se disponível)
            if (tableData.columns && tableData.columns.some(c => c.stats)) {{
                const statsColumns = tableData.columns.filter(c => c.stats && (c.stats.null_count !== undefined || c.stats.unique_count !== undefined || c.stats.min_value !== undefined || c.stats.max_value !== undefined));
                if (statsColumns.length > 0) {{
                    modalBody += `
                        <div class="modal-section">
                            <h3>Estatísticas das Colunas</h3>
                            <div class="table-wrapper">
                                <table class="columns-table">
                                    <thead>
                                        <tr>
                                            <th>Coluna</th>
                                            <th>Valores Nulos</th>
                                            <th>% Nulos</th>
                                            <th>Valores Únicos</th>
                                            <th>Mínimo</th>
                                            <th>Máximo</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    statsColumns.forEach(col => {{
                        const nullCount = col.stats.null_count !== undefined ? col.stats.null_count : "-";
                        const nullCountPercentage = (col.stats.null_count !== undefined && tableData.row_count) ? ((col.stats.null_count / tableData.row_count) * 100).toFixed(2) + "%" : "-";
                        const uniqueCount = col.stats.distinct_count !== undefined ? col.stats.distinct_count : "-";
                        const min = col?.stats?.numeric_stats?.min;
                        const max = col?.stats?.numeric_stats?.max;

                        const minValue = min != null ? String(min).substring(0, 50) : "-";
                        const maxValue = max != null ? String(max).substring(0, 50) : "-";
                        modalBody += `
                            <tr>
                                <td><strong>${{col.name}}</strong></td>
                                <td>${{nullCount}}</td>
                                <td>${{nullCountPercentage}}</td>
                                <td>${{uniqueCount}}</td>
                                <td title="${{minValue}}">${{minValue}}</td>
                                <td title="${{maxValue}}">${{maxValue}}</td>
                            </tr>
                        `;
                    }});
                    modalBody += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                }}
            }}
            
            document.getElementById("modal-body").innerHTML = modalBody;
            document.getElementById("modal-overlay").classList.add("active");
        }}

        function addFinding(type, title, details, origin, event) {{
            if (type !== "Tabela" || savedTableNames.has(title)) {{
                return;
            }}
            
            const id = Date.now();
            const cleanTableName = title.includes(".") ? title.split(".")[1] : title;
            const tableData = metadataDict[cleanTableName];
            
            let macrotemaInfo = "";
            let temasRelacionados = [];
            
            data.forEach(d => {{
                if (d.themes) {{
                    d.themes.forEach(t => {{
                        if (t.tables && t.tables.includes(title)) {{
                            if (d.macro && !macrotemaInfo) macrotemaInfo = d.macro;
                            if (!temasRelacionados.includes(t.theme)) temasRelacionados.push(t.theme);
                        }}
                    }});
                }}
            }});
            
            const rowCount = tableData?.row_count || "N/A";
            const columnCount = tableData?.columns?.length || "N/A";
            const columnDetails = tableData?.columns
            ? tableData.columns.map(c => ({{
                name: c.name,
                type: c.type,
                sample_values: c.stats.sample_values ? c.stats.sample_values.slice(0, 5) : []
                }}))
            : []; 
            
            findings.push({{ 
                id, 
                type: "Tabela", 
                title, 
                macrotema: macrotemaInfo || "N/A",
                temas: temasRelacionados,
                rowCount,
                columnCount,
                columnDetails,
                origin: origin || "N/A", 
                date: new Date().toLocaleString(), 
                saved: true 
            }});
            
            savedTableNames.add(title);
            localStorage.setItem('som_findings', JSON.stringify(findings));
            updateFindingsCount();
            
            if (event && event.target) {{
                const btn = event.target;
                btn.innerText = "✓ Salvo";
                btn.style.background = "#2ecc71";
                btn.disabled = true;
            }}
            
            if (selectedNeuronId) {{
                const d = data.find(x => x.id === selectedNeuronId);
                updateSidebar(d);
            }}
            
            if (document.getElementById("findings-panel").style.display !== "none") {{
                updateFindingsList();
            }}
        }}

        function removeFinding(id) {{
            const finding = findings.find(f => f.id === id);
            if (finding) {{
                savedTableNames.delete(finding.title);
            }}
            findings = findings.filter(f => f.id !== id);
            localStorage.setItem('som_findings', JSON.stringify(findings));
            updateFindingsCount();
            updateFindingsList();
            
            if (selectedNeuronId) {{
                const d = data.find(x => x.id === selectedNeuronId);
                updateSidebar(d);
            }}
            
            const modalTitle = document.getElementById("modal-table-name").textContent;
            if (finding && finding.title === modalTitle) {{
                const addBtn = document.getElementById("add-table-finding-btn");
                addBtn.innerText = "Salvar Tabela";
                addBtn.style.background = "";
                addBtn.disabled = false;
                const cleanTableName = modalTitle.includes('.') ? modalTitle.split('.')[1] : modalTitle;
                const tableData = metadataDict[cleanTableName];
                addBtn.onclick = (e) => addFinding('Tabela', modalTitle.replace(/'/g, "\\\\'"), `Linhas: ${{tableData.row_count || "N/A"}} | Colunas: ${{tableData.columns ? tableData.columns.length : "N/A"}}`, modalTitle, e);
            }}
        }}

        function updateFindingsCount() {{
            document.getElementById("findings-count").innerText = findings.length;
        }}

        function updateFindingsList() {{
            const list = document.getElementById("findings-list");
            if (findings.length === 0) {{
                list.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 40px 0; font-style: italic; font-size: 0.8rem;">Nenhum achado salvo ainda.<br>Clique em "Salvar" nas tabelas.</div>`;
                return;
            }}
            
            list.innerHTML = findings.map(f => `
                <div class="finding-item" onclick="openTableModal('${{f.title.replace(/'/g, "\\'")}}')">
                    <button class="remove-btn" onclick="event.stopPropagation(); removeFinding(${{f.id}})" title="Remover">&times;</button>
                    <span class="finding-type">Tabela</span>
                    <span class="finding-title">${{f.title}}</span>
                    <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 4px;">
                        <strong>Macrotema:</strong> ${{f.macrotema}}
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 2px;">
                        <strong>Linhas:</strong> ${{f.rowCount}} | <strong>Colunas:</strong> ${{f.columnCount}}
                    </div>
                    <div style="color: var(--text-muted); font-size: 0.6rem; margin-top: 8px; text-align: right;">
                        ${{f.date}}
                    </div>
                    ${{f.saved ? '<span class="finding-status">✓ Salvo</span>' : ''}}
                </div>
            `).join("");
        }}

        function exportFindings(format) {{
            if (findings.length === 0) {{
                alert("Adicione alguns achados antes de exportar!");
                return;
            }}
            
            let content = "";
            const customFilename = document.getElementById("download-filename").value.trim();
            let filename = (customFilename || "meus_achados_som") + "." + format;
            let mimeType = "text/plain";
            
            if (format === 'json') {{
                content = JSON.stringify(findings, null, 2);
                mimeType = "application/json";
                
            }} else if (format === 'csv') {{
                const headers = [
                    "Tabela", 
                    "Macrotema", 
                    "Temas", 
                    "Linhas", 
                    "Colunas", 
                    "Detalhes das Colunas",
                    "Data"
                ];

                const rows = findings.map(f => {{
                    const columnDetailsStr = (f.columnDetails || [])
                        .map(c => `${{c.name}} (${{c.type}}) [${{(c.sample_values || []).join(" | ")}}]`)
                        .join(" || ");

                    return [
                        f.title, 
                        f.macrotema, 
                        f.temas.join("; "),
                        f.rowCount,
                        f.columnCount,
                        columnDetailsStr,
                        f.date
                    ]
                    .map(v => `"${{String(v).replace(/"/g, '""')}}"`
                    ).join(",");
                }});

                content = headers.join(",") + "\\n" + rows.join("\\n");
                mimeType = "text/csv";
                
            }} else if (format === 'md') {{
                content = "# Relatório de Achados - Análise SOM\\n\\n";
                content += `Gerado em: ${{new Date().toLocaleString()}}\\n\\n`;

                findings.forEach(f => {{
                    content += `## ${{f.title}}\\n`;
                    content += `- **Macrotema:** ${{f.macrotema}}\\n`;
                    content += `- **Temas Relacionados:** ${{f.temas.length > 0 ? f.temas.join(", ") : "Nenhum"}}\\n`;
                    content += `- **Linhas:** ${{f.rowCount}}\\n`;
                    content += `- **Colunas:** ${{f.columnCount}}\\n`;

                    content += `- **Detalhes das Colunas:**\\n`;
                    if (f.columnDetails && f.columnDetails.length > 0) {{
                        f.columnDetails.forEach(c => {{
                            content += `  - ${{c.name}} (${{c.type}}) → exemplos: ${
                                "{(c.sample_values || []).join(', ') || 'N/A'}"
                            }\\n`;
                        }});
                    }} else {{
                        content += `  - Nenhum detalhe disponível\\n`;
                    }}

                    content += `- **Data:** ${{f.date}}\\n\\n`;
                }});

                mimeType = "text/markdown";
            }}
            
            const blob = new Blob([content], {{ type: mimeType }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }}

        // Fechar modal ao clicar fora
        document.getElementById("modal-overlay").addEventListener("click", function(e) {{
            if (e.target === this) closeTableModal();
        }});

        // Fechar modal com Escape
        document.addEventListener("keydown", function(e) {{
            if (e.key === "Escape") closeTableModal();
        }});

        document.getElementById("search-macro").addEventListener("input", (e) => {{ macroQuery = e.target.value; applyFilters(); }});
        document.getElementById("search-theme").addEventListener("input", (e) => {{ themeQuery = e.target.value; applyFilters(); }});
        window.addEventListener("resize", () => {{ render(); }});
        
        // Inicialização
        setTimeout(() => {{ 
            render(); 
            buildLegend(); 
            updateFindingsCount();
        }}, 100);
    </script>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f: f.write(html)
