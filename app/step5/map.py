from collections import defaultdict, Counter
import json

from matplotlib import cm
try:
    from matplotlib import colormaps
except ImportError:
    colormaps = None
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
    # Associação direta tabela -> tema. O tema é a classificação específica da
    # tabela; o macrotema agregado do neurônio não deve ser usado neste detalhe.
    table_to_theme = {}
    for m in macrothemes:
        for theme_name in (m.get("subtemas") or []):
            for table_name in (tables_by_theme.get(theme_name, []) or []):
                clean_table = table_name.split(".")[-1] if isinstance(table_name, str) else table_name
                table_to_theme.setdefault(clean_table, theme_name)

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
    table_theme_json = json.dumps(table_to_theme, ensure_ascii=False)

    # Preparar dados de U-Matrix normalizada para colormap inferno
    umatrix_min = float(np.min(umatrix))
    umatrix_max = float(np.max(umatrix))
    umatrix_range = umatrix_max - umatrix_min if umatrix_max > umatrix_min else 1.0
    
    # Criar mapa de cores inferno normalizado
    cmap_inferno = colormaps.get_cmap('inferno') if colormaps is not None else cm.get_cmap('inferno')
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
        
        /* ===== MODAL OVERLAY ===== */
        #modal-overlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.72); z-index: 3000;
            align-items: center; justify-content: center; padding: 20px;
        }}
        #modal-overlay.active {{ display: flex; }}
        .modal-content {{
            background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
            max-width: 1100px; width: 95%; max-height: 88vh; overflow: hidden;
            padding: 0; box-shadow: 0 20px 60px rgba(0,0,0,0.9);
            display: flex; flex-direction: column;
            transition: transform 0.25s, filter 0.25s;
            position: relative;
        }}

        /* Breadcrumb navbar */
        .modal-breadcrumb {{
            display: flex; align-items: center; gap: 0; padding: 7px 18px;
            background: rgba(0,0,0,0.3); border-bottom: 1px solid var(--border);
            font-size: 0.72rem; overflow-x: auto; flex-shrink: 0; flex-wrap: nowrap;
            scrollbar-width: none;
        }}
        .modal-breadcrumb::-webkit-scrollbar {{ display: none; }}
        .bc-item {{
            display: flex; align-items: center; gap: 4px; white-space: nowrap;
        }}
        .bc-name {{
            color: var(--text-muted); cursor: pointer; padding: 2px 5px; border-radius: 3px;
            transition: color 0.15s, background 0.15s;
        }}
        .bc-name:hover {{ color: var(--primary); background: rgba(255,159,67,0.1); }}
        .bc-name.current {{ color: var(--primary); font-weight: 700; cursor: default; }}
        .bc-name.current:hover {{ background: none; }}
        .bc-sep {{ color: var(--border); margin: 0 1px; }}

        .modal-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 0; border-bottom: 1px solid var(--border); padding: 14px 22px;
            flex-shrink: 0; background: var(--surface);
        }}
        .modal-header h2 {{
            margin: 0; font-size: 1.2rem; color: var(--text); word-break: break-word;
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
            background: var(--primary); color: #000; border: none; padding: 0 16px;
            border-radius: 6px; cursor: pointer; font-weight: 700; font-size: 0.82rem;
            transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px;
            height: 34px;
        }}
        .add-finding-btn:hover {{ opacity: 0.9; }}
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

        /* ===== RELATIONSHIP GRAPH MODAL ===== */
        #graph-modal-overlay {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); z-index: 4000; align-items: center; justify-content: center;
        }}
        #graph-modal-overlay.active {{ display: flex; }}
        #graph-modal {{
            background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
            width: 98vw; max-width: 1700px; height: 95vh; display: flex; flex-direction: column;
            box-shadow: 0 30px 80px rgba(0,0,0,0.95); overflow: hidden;
        }}
        #graph-modal-header {{
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 22px; border-bottom: 1px solid var(--border); flex-shrink: 0;
        }}
        #graph-modal-header h2 {{ margin: 0; font-size: 1.05rem; color: var(--primary); }}
        #graph-modal-header .subtitle {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 3px; }}
        #graph-modal-close {{
            background: none; border: none; color: var(--text); font-size: 1.5rem;
            cursor: pointer; padding: 0; width: 30px; height: 30px;
            display: flex; align-items: center; justify-content: center;
        }}
        #graph-modal-close:hover {{ color: var(--primary); }}
        #graph-modal-body {{
            display: flex; flex: 1; overflow: hidden;
        }}
        #graph-svg-container {{
            flex: 1; position: relative; background: var(--bg);
        }}
        #graph-svg {{ width: 100%; height: 100%; }}
        #graph-info-panel {{
            width: 340px; border-left: 1px solid var(--border); padding: 18px;
            overflow-y: auto; flex-shrink: 0; font-size: 0.8rem;
        }}
        #graph-info-panel h3 {{ margin: 0 0 12px; font-size: 0.85rem; color: var(--primary); }}
        .graph-info-placeholder {{ color: var(--text-muted); font-style: italic; font-size: 0.8rem; margin-top: 20px; text-align: center; }}
        .graph-legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 0.75rem; color: var(--text-muted); }}
        .graph-legend-dot {{ width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }}
        .graph-node-detail {{ background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px; }}
        .graph-node-detail .detail-label {{ font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 3px; }}
        .graph-node-detail .detail-value {{ font-size: 0.82rem; font-weight: 600; word-break: break-all; }}
        .graph-fk-list {{ margin-top: 10px; }}
        .graph-fk-item {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 0.72rem; cursor: pointer; transition: border-color 0.2s; }}
        .graph-fk-item:hover {{ border-color: var(--primary); }}
        .graph-fk-item .fk-table {{ font-weight: 700; color: var(--text); margin-bottom: 3px; }}
        .graph-fk-item .fk-cols {{ color: var(--text-muted); font-size: 0.68rem; }}
        .fk-direction {{ font-size: 0.6rem; text-transform: uppercase; font-weight: bold; padding: 1px 5px; border-radius: 3px; display: inline-block; margin-bottom: 4px; }}
        .fk-out {{ background: rgba(255,159,67,0.2); color: var(--primary); }}
        .fk-in  {{ background: rgba(100,200,100,0.2); color: #2ecc71; }}
        #graph-depth-toggle {{ display: flex; gap: 6px; margin-bottom: 14px; }}
        .graph-depth-card {{
            background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
            padding: 12px; margin-bottom: 18px;
        }}
        .graph-depth-title {{
            color: var(--text); font-size: 0.78rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
        }}
        .graph-depth-help {{ color: var(--text-muted); font-size: 0.7rem; line-height: 1.55; margin-bottom: 10px; }}
        .depth-btn {{
            flex: 1; padding: 5px; border: 1px solid var(--border); border-radius: 4px;
            background: var(--bg); color: var(--text-muted); font-size: 0.72rem; cursor: pointer;
        }}
        .depth-btn.active {{ background: var(--primary); color: #000; border-color: var(--primary); font-weight: bold; }}
        #open-graph-btn {{
            background: var(--bg); color: var(--primary); border: 1px solid var(--primary);
            padding: 0 16px; border-radius: 6px; cursor: pointer; font-size: 0.8rem;
            font-weight: 600; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px;
            height: 34px; margin-top: 0;
        }}
        #open-graph-btn:hover {{ background: var(--primary); color: #000; }}
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

    <!-- MODAL DE TABELA -->
    <div id="modal-overlay" onclick="if(event.target===this) closeTableModal()">
        <div class="modal-content" id="modal-content-inner">
            <div class="modal-breadcrumb" id="modal-breadcrumb"></div>
            <div class="modal-header">
                <h2 id="modal-table-name">—</h2>
                <div style="display:flex;align-items:center;gap:10px;">
                    <button id="modal-graph-btn" style="background:var(--bg);color:var(--primary);border:1px solid var(--primary);padding:0 16px;border-radius:6px;cursor:pointer;font-size:0.8rem;font-weight:600;height:34px;display:inline-flex;align-items:center;gap:6px;">&#9901; Ver Relacionamentos</button>
                    <button id="modal-save-btn" class="add-finding-btn">Salvar Tabela</button>
                    <button class="modal-close" onclick="closeTableModal()">&times;</button>
                </div>
            </div>
            <div class="modal-body" id="modal-body"></div>
        </div>
    </div>

    <!-- MODAL DE GRAFO DE RELACIONAMENTOS -->
    <div id="graph-modal-overlay" onclick="if(event.target===this) closeGraphModal()">
        <div id="graph-modal">
            <div id="graph-modal-header">
                <div>
                    <h2 id="graph-modal-title">Relacionamentos</h2>
                    <div class="subtitle" id="graph-modal-subtitle"></div>
                </div>
                <button id="graph-modal-close" onclick="closeGraphModal()">&times;</button>
            </div>
            <div id="graph-modal-body">
                <div id="graph-svg-container">
                    <svg id="graph-svg"></svg>
                </div>
                <div id="graph-info-panel">
                    <div class="graph-depth-card">
                        <div class="graph-depth-title">Profundidade do grafo</div>
                        <div class="graph-depth-help">
                            <strong style="color:var(--text);">Nível 1</strong> · relações diretas da tabela principal<br>
                            <strong style="color:var(--text);">Nível 2</strong> · relações das tabelas do nível 1
                        </div>
                        <div id="graph-depth-toggle">
                            <button class="depth-btn active" onclick="setGraphDepth(1, this)">1</button>
                            <button class="depth-btn" onclick="setGraphDepth(2, this)">2</button>
                        </div>
                    </div>
                    <h3>Legenda</h3>
                    <div class="graph-legend-item">
                        <div class="graph-legend-dot" style="background:#ff9f43; border: 2px solid #fff;"></div>
                        <span>Tabela principal</span>
                    </div>
                    <div class="graph-legend-item">
                        <div class="graph-legend-dot" style="background:#636EFA;"></div>
                        <span>Referencia outra (FK saindo)</span>
                    </div>
                    <div class="graph-legend-item">
                        <div class="graph-legend-dot" style="background:#2ecc71;"></div>
                        <span>Referenciada por outra (FK entrando)</span>
                    </div>
                    <div class="graph-legend-item">
                        <div class="graph-legend-dot" style="background:#AB63FA;"></div>
                        <span>Nível 2 (vizinhos de vizinhos)</span>
                    </div>
                    <div style="margin: 14px 0 6px; font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Nó selecionado</div>
                    <div id="graph-node-info"><div class="graph-info-placeholder">Clique em um nó para ver detalhes</div></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const data = {data_json};
        const macros = {macros_json};
        const metadataDict = {metadata_json};
        const tableThemeMap = {table_theme_json};
        const umatrixColors = {umatrix_colors_json};
        const svg = d3.select("#viz");
        const g = svg.append("g");
        const tooltip = d3.select("#tooltip");
        const sidebar = d3.select("#sidebar");

        // ===== NORMALIZAÇÃO DE TEXTO PARA BUSCA (remove acentos, trata hífen/underline/espaço) =====
        function normalizeText(str) {{
            return (str || "")
                .toString()
                .normalize("NFD")
                .replace(/[\\u0300-\\u036f]/g, "")
                .toLowerCase()
                .replace(/[-_\\s]+/g, " ")
                .trim();
        }}

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
            
            const tQ = normalizeText(themeQuery);
            const sF = normalizeText(sidebarFilter);
            
            const filteredThemes = d.themes.filter(t => 
                (sF === "" || normalizeText(t.theme).includes(sF))
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
                const match = tQ !== "" && normalizeText(t.theme).includes(tQ);
                const highlightStyle = match ? 'style="background: rgba(255, 159, 67, 0.15); border-left: 3px solid var(--primary); padding-left: 8px;"' : 'style="padding-left: 8px;"';
                
                const tablesHtml = t.tables && t.tables.length > 0 
                    ? `<div style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px;">
                         ${{t.tables.map(tab => {{
                             const isSaved = savedTableNames.has(tab);
                             const savedClass = isSaved ? 'saved' : '';
                             const savedIcon = isSaved ? '✓ ' : '';
                             return `<span class="table-tag ${{savedClass}}" onclick="openTableModal(decodeURIComponent('${{encodeURIComponent(tab)}}'), decodeURIComponent('${{encodeURIComponent(t.theme)}}'))">${{savedIcon}}${{tab}}</span>`;
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
            const tQ = normalizeText(themeQuery);
            const visibleThemes = d.themes.slice(0, 10);
            content += visibleThemes.map(t => {{
                const match = tQ !== "" && normalizeText(t.theme).includes(tQ);
                const style = match ? 'style="color:var(--primary); font-weight:bold;"' : '';
                return `<div ${{style}}>• ${{t.theme}} (${{t.freq}})</div>`;
            }}).join("");
            if(d.themes.length > 10) content += `<div style="color:var(--primary); margin-top:4px;">+ ${{d.themes.length - 10}} outros (veja na lateral)</div>`;
            tooltip.html(content);
        }}

        function applyFilters() {{
            const mQ = normalizeText(macroQuery);
            const tQ = normalizeText(themeQuery);
            g.selectAll(".hexagon:not(.empty)").each(function(d) {{
                const macroName = normalizeText(d.macro || "");
                const hasMacroMatch = mQ === "" || macroName.includes(mQ);
                const isMacroActive = !activeMacro || d.macro === activeMacro;
                const hasThemeMatch = tQ === "" || d.themes.some(t => normalizeText(t.theme).includes(tQ));
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

        // ===== MODAL DE TABELA COM HISTÓRICO (BREADCRUMB) =====
        let modalStack = [];   // [{{tableName}}]

        function renderBreadcrumb() {{
            const bc = document.getElementById('modal-breadcrumb');
            if (!bc) return;
            bc.innerHTML = modalStack.map((item, i) => {{
                const isLast = i === modalStack.length - 1;
                const name = item.tableName.includes('.') ? item.tableName.split('.')[1] : item.tableName;
                const sep = i > 0 ? '<span class="bc-sep">›</span>' : '';
                if (isLast) return sep + `<span class="bc-item"><span class="bc-name current">${{name}}</span></span>`;
                return sep + `<span class="bc-item"><span class="bc-name" onclick="popModalStackTo(${{i}})">${{name}}</span></span>`;
            }}).join('');
        }}

        function popModalStackTo(idx) {{
            modalStack = modalStack.slice(0, idx + 1);
            const top = modalStack[modalStack.length - 1];
            _renderTableModal(top.tableName, false);
        }}

        function closeTableModal() {{
            if (modalStack.length > 1) {{
                modalStack.pop();
                const top = modalStack[modalStack.length - 1];
                _renderTableModal(top.tableName, false);
            }} else {{
                modalStack = [];
                document.getElementById('modal-overlay').classList.remove('active');
                document.getElementById('modal-overlay').style.zIndex = '';
            }}
        }}

        function closeAllTableModals() {{
            modalStack = [];
            document.getElementById('modal-overlay').classList.remove('active');
            document.getElementById('modal-overlay').style.zIndex = '';
        }}

        function openTableModal(tableName, sourceTheme = null) {{
            const cleanTableName = tableName.includes('.') ? tableName.split('.')[1] : tableName;
            const tableData = metadataDict[cleanTableName];
            if (!tableData) {{ alert(`Tabela "${{tableName}}" não encontrada.`); return; }}
            modalStack.push({{ tableName, sourceTheme }});
            // Se grafo está aberto, ficar acima dele
            const graphIsOpen = document.getElementById('graph-modal-overlay').classList.contains('active');
            document.getElementById('modal-overlay').style.zIndex = graphIsOpen ? '5000' : '3000';
            _renderTableModal(tableName, true);
        }}

        function _renderTableModal(tableName, open, sourceTheme = null) {{
            const cleanTableName = tableName.includes('.') ? tableName.split('.')[1] : tableName;
            const tableData = metadataDict[cleanTableName];
            const stackIdx = modalStack.length - 1;

            document.getElementById('modal-table-name').textContent = tableName;

            // Botão de grafo
            const graphBtn = document.getElementById('modal-graph-btn');
            graphBtn.onclick = () => openRelationshipGraph(cleanTableName);

            // Botão de salvar
            const saveBtn = document.getElementById('modal-save-btn');
            const isSaved = savedTableNames.has(tableName);
            saveBtn.innerText = isSaved ? '✓ Salvo' : 'Salvar Tabela';
            saveBtn.style.background = isSaved ? '#2ecc71' : '';
            saveBtn.style.color = isSaved ? '#fff' : '';
            saveBtn.disabled = isSaved;
            saveBtn.onclick = () => {{
                addFinding('Tabela', tableName, `Linhas: ${{tableData?.row_count || "N/A"}}`, tableName, null);
                saveBtn.innerText = '✓ Salvo';
                saveBtn.style.background = '#2ecc71';
                saveBtn.style.color = '#fff';
                saveBtn.disabled = true;
            }};

            const selectedTheme = sourceTheme || modalStack[stackIdx]?.sourceTheme || null;
            document.getElementById('modal-body').innerHTML = buildTableModalBody(tableName, tableData, stackIdx, selectedTheme);
            renderBreadcrumb();

            if (open) document.getElementById('modal-overlay').classList.add('active');
        }}

        function saveTableFromStack(stackIdx, tableName) {{}}  // compatibilidade
        function updateSaveBtnState(stackIdx, tableName) {{}}  // compatibilidade
        function updateAllBreadcrumbs() {{ renderBreadcrumb(); }}

        function buildTableModalBody(tableName, tableData, stackIdx, selectedTheme = null) {{
            // Quando o clique veio do sidebar, usar o tema daquela linha exatamente.
            const cleanTableName = tableName.includes('.') ? tableName.split('.').pop() : tableName;
            const tableModalTheme = selectedTheme || tableThemeMap[cleanTableName] || "—";

            let modalBody = `
                <div class="modal-section">
                    <h3>Informações da Tabela</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Nome</div>
                            <div class="info-value">${{tableName}}</div>
                        </div>
                        <div class="info-item" style="border-color: var(--primary); background: rgba(255,159,67,0.07);">
                            <div class="info-label">Tema</div>
                            <div class="info-value" style="color: var(--primary); font-size: 0.82rem;">${{tableModalTheme}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Linhas</div>
                            <div class="info-value">${{(tableData.row_count || 0).toLocaleString() || "N/A"}}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Colunas</div>
                            <div class="info-value">${{tableData.columns ? tableData.columns.length : "N/A"}}</div>
                        </div>
                    </div>
                </div>
            `;

            // Seção de Chaves Estrangeiras
            const fks = tableData.foreign_keys || [];
            if (fks.length > 0) {{
                modalBody += `
                    <div class="modal-section">
                        <h3>Chaves Estrangeiras (${{fks.length}})</h3>
                        <div class="table-wrapper">
                            <table class="columns-table">
                                <thead>
                                    <tr>
                                        <th>Nome</th>
                                        <th>Coluna(s) local</th>
                                        <th>Tabela referenciada</th>
                                        <th>Coluna(s) referenciada</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                fks.forEach(fk => {{
                    modalBody += `
                        <tr>
                            <td style="color:var(--text-muted);font-size:0.75rem;">${{fk.name || "—"}}</td>
                            <td><strong>${{(fk.constrained_columns || []).join(", ")}}</strong></td>
                            <td>
                                <span class="table-tag" style="cursor:pointer;" onclick="openTableModal('${{fk.referred_table}}')">
                                    ${{fk.referred_table}}
                                </span>
                            </td>
                            <td style="color:var(--text-muted);">${{(fk.referred_columns || []).join(", ")}}</td>
                        </tr>
                    `;
                }});
                modalBody += `</tbody></table></div></div>`;
            }}

            // Seção de Colunas
            if (tableData.columns && tableData.columns.length > 0) {{
                modalBody += `
                    <div class="modal-section">
                        <h3>Colunas (${{tableData.columns.length}})</h3>
                        <div class="table-wrapper">
                            <table class="columns-table">
                                <thead>
                                    <tr><th>Nome</th><th>Tipo</th><th>Nullable</th><th>Exemplos</th></tr>
                                </thead>
                                <tbody>
                `;
                tableData.columns.forEach(col => {{
                    const nullable = col.nullable ? "Sim" : "Não";
                    let examples = "";
                    if (col.stats && col.stats.sample_values && col.stats.sample_values.length > 0) {{
                        examples = col.stats.sample_values.slice(0, 3)
                            .map(v => v !== null && v !== undefined ? String(v) : "NULL").join(", ");
                        if (col.stats.sample_values.length > 3) examples += "...";
                    }}
                    modalBody += `
                        <tr>
                            <td><strong>${{col.name}}</strong></td>
                            <td>${{col.type || "—"}}</td>
                            <td>${{nullable}}</td>
                            <td title="${{examples || "—"}}"><span class="sample-values">${{examples || "—"}}</span></td>
                        </tr>`;
                }});
                modalBody += `</tbody></table></div></div>`;
            }}

            // Seção de Estatísticas
            if (tableData.columns && tableData.columns.some(c => c.stats)) {{
                const statsColumns = tableData.columns.filter(c => c.stats && (
                    c.stats.null_count !== undefined || c.stats.unique_count !== undefined ||
                    c.stats.min_value !== undefined || c.stats.max_value !== undefined));
                if (statsColumns.length > 0) {{
                    modalBody += `
                        <div class="modal-section">
                            <h3>Estatísticas das Colunas</h3>
                            <div class="table-wrapper">
                                <table class="columns-table">
                                    <thead>
                                        <tr><th>Coluna</th><th>Valores Nulos</th><th>% Nulos</th><th>Valores Únicos</th><th>Mínimo</th><th>Máximo</th></tr>
                                    </thead>
                                    <tbody>`;
                    statsColumns.forEach(col => {{
                        const nullCount = col.stats.null_count !== undefined ? col.stats.null_count : "-";
                        const nullPct = (col.stats.null_count !== undefined && tableData.row_count)
                            ? ((col.stats.null_count / tableData.row_count) * 100).toFixed(2) + "%" : "-";
                        const uniqueCount = col.stats.distinct_count !== undefined ? col.stats.distinct_count : "-";
                        const min = col?.stats?.numeric_stats?.min;
                        const max = col?.stats?.numeric_stats?.max;
                        const minVal = min != null ? String(min).substring(0, 50) : "-";
                        const maxVal = max != null ? String(max).substring(0, 50) : "-";
                        modalBody += `
                            <tr>
                                <td><strong>${{col.name}}</strong></td>
                                <td>${{nullCount}}</td><td>${{nullPct}}</td>
                                <td>${{uniqueCount}}</td>
                                <td title="${{minVal}}">${{minVal}}</td>
                                <td title="${{maxVal}}">${{maxVal}}</td>
                            </tr>`;
                    }});
                    modalBody += `</tbody></table></div></div>`;
                }}
            }}
            return modalBody;
        }}

        function addFinding(type, title, details, origin, event) {{
            if (type !== "Tabela" || savedTableNames.has(title)) {{
                return;
            }}
            
            const id = Date.now();
            const cleanTableName = title.includes(".") ? title.split(".")[1] : title;
            const tableData = metadataDict[cleanTableName];
            
            let macrotemaInfo = tableThemeMap[cleanTableName.split('.').pop()] || "";
            let temasRelacionados = [];
            
            data.forEach(d => {{
                if (d.themes) {{
                    d.themes.forEach(t => {{
                        if (t.tables && t.tables.includes(title)) {{
                            if (!macrotemaInfo) macrotemaInfo = t.theme || "";
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
                        <strong>Tema:</strong> ${{f.macrotema}}
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
                    "Tema", 
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
                    content += `- **Tema:** ${{f.macrotema}}\\n`;
                    content += `- **Temas Relacionados:** ${{f.temas.length > 0 ? f.temas.join(", ") : "Nenhum"}}\\n`;
                    content += `- **Linhas:** ${{f.rowCount}}\\n`;
                    content += `- **Colunas:** ${{f.columnCount}}\\n`;

                    content += `- **Detalhes das Colunas:**\\n`;
                    if (f.columnDetails && f.columnDetails.length > 0) {{
                        f.columnDetails.forEach(c => {{
                            const samples = (c.sample_values || []).join(', ') || 'N/A';
                            content += `  - ${{c.name}} (${{c.type}}) → exemplos: ${{samples}}\\n`;
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

        // ===== GRAFO DE RELACIONAMENTOS =====

        let currentGraphTable = null;
        let currentGraphDepth = 1;
        let graphSimulation = null;

        function buildGraphData(rootTable, depth) {{
            const nodes = new Map();
            const links = [];
            const linkKeys = new Set();

            function cleanName(name) {{
                return (name || "").includes('.') ? name.split('.').pop() : (name || "");
            }}
            function metadataFor(name) {{
                if (metadataDict[name]) return metadataDict[name];
                const clean = cleanName(name);
                const key = Object.keys(metadataDict).find(k => cleanName(k) === clean);
                return key ? metadataDict[key] : null;
            }}
            function canonicalName(name) {{
                const clean = cleanName(name);
                const key = Object.keys(metadataDict).find(k => cleanName(k) === clean);
                return key || name;
            }}
            function macroFor(name) {{
                const clean = cleanName(name);
                return tableThemeMap[clean] || "—";
            }}
            function addNode(name, role, level) {{
                const id = canonicalName(name);
                const d = metadataFor(id) || {{}};
                const old = nodes.get(id);
                if (!old || level < old.level) {{
                    nodes.set(id, {{
                        id, role: id === rootTable ? "root" : role, level,
                        row_count: d.row_count || 0,
                        col_count: d.columns ? d.columns.length : 0,
                        fk_count: d.foreign_keys ? d.foreign_keys.length : 0,
                        macro: macroFor(id)
                    }});
                }}
                return id;
            }}
            function addLink(source, target, direction, fk) {{
                const s = canonicalName(source), t = canonicalName(target);
                const key = `${{s}}→${{t}}|${{fk.name || ""}}|${{(fk.constrained_columns || []).join(",")}}`;
                if (linkKeys.has(key)) return;
                linkKeys.add(key);
                links.push({{
                    source: s, target: t, direction,
                    label: (fk.constrained_columns || []).join(", ") + " → " + (fk.referred_columns || []).join(", "),
                    fk_name: fk.name
                }});
            }}

            const root = canonicalName(rootTable);
            addNode(root, "root", 0);
            const queue = [root];
            const distances = new Map([[root, 0]]);
            while (queue.length) {{
                const current = queue.shift();
                const currentLevel = distances.get(current);
                if (currentLevel >= depth) continue;
                const currentData = metadataFor(current) || {{}};

                // Caminho de FK saindo: current referencia target.
                (currentData.foreign_keys || []).forEach(fk => {{
                    const target = canonicalName(fk.referred_table);
                    const next = currentLevel + 1;
                    addNode(target, currentLevel === 0 ? "out" : "secondary", next);
                    addLink(current, target, "out", fk);
                    if (!distances.has(target)) {{ distances.set(target, next); queue.push(target); }}
                }});

                // Caminho de FK entrando: other referencia current.
                Object.entries(metadataDict).forEach(([otherName, otherData]) => {{
                    (otherData.foreign_keys || []).forEach(fk => {{
                        if (canonicalName(fk.referred_table) !== current) return;
                        const other = canonicalName(otherName);
                        const next = currentLevel + 1;
                        addNode(other, currentLevel === 0 ? "in" : "secondary", next);
                        addLink(other, current, "in", fk);
                        if (!distances.has(other)) {{ distances.set(other, next); queue.push(other); }}
                    }});
                }});
            }}
            return {{ nodes: Array.from(nodes.values()), links }};
        }}

        function nodeColor(d) {{
            if (d.role === "root") return "#ff9f43";
            if (d.role === "out") return "#636EFA";
            if (d.role === "in") return "#2ecc71";
            return "#AB63FA";
        }}

        function nodeRadius(d) {{
            if (d.role === "root") return 22;
            const base = 10 + Math.min(d.col_count * 0.5, 10);
            return d.level === 1 ? base + 2 : base - 2;
        }}

        function renderGraph(rootTable, depth) {{
            const container = document.getElementById("graph-svg-container");
            const W = container.clientWidth;
            const H = container.clientHeight;
            const cx = W / 2, cy = H / 2;

            const svgEl = d3.select("#graph-svg");
            svgEl.selectAll("*").remove();

            const {{ nodes, links }} = buildGraphData(rootTable, depth);

            document.getElementById("graph-modal-subtitle").textContent =
                `${{nodes.length}} tabelas · ${{links.length}} relacionamentos`;

            if (nodes.length <= 1) {{
                svgEl.append("text")
                    .attr("x", cx).attr("y", cy)
                    .attr("text-anchor", "middle")
                    .attr("fill", "var(--text-muted)")
                    .attr("font-size", "14px")
                    .text("Esta tabela não possui relacionamentos de FK registrados.");
                return;
            }}

            // ── Zoom / pan ──────────────────────────────────────────────
            const gZoom = svgEl.append("g");
            const zoomBehavior = d3.zoom().scaleExtent([0.15, 5])
                .on("zoom", e => gZoom.attr("transform", e.transform))
                .filter(event => {{
                    // Scroll e arraste continuam disponíveis; clique simples não altera a viewport.
                    if (event.type === 'wheel') return true;
                    if (event.type === 'touchstart') return true;
                    if (event.type === 'dblclick') return false; // desabilita zoom no dblclick
                    return event.type === 'mousedown' && event.button === 0 && !event.ctrlKey;
                }});
            svgEl.call(zoomBehavior);

            // ── Layout radial generalizado para N níveis ─────────────────
            const maxLevel = Math.max(...nodes.map(n => n.level));
            const baseR = Math.min(W, H) * 0.32;
            // Raios crescentes por nível
            const radiiByLevel = Array.from({{length: maxLevel + 1}}, (_, i) =>
                i === 0 ? 0 : baseR * (0.9 + (i - 1) * 0.55)
            );

            function placeArc(arr, rRadius, startAngle, endAngle) {{
                arr.forEach((n, i) => {{
                    const t = arr.length === 1 ? 0.5 : i / (arr.length - 1);
                    const angle = startAngle + t * (endAngle - startAngle);
                    n.px = cx + rRadius * Math.cos(angle);
                    n.py = cy + rRadius * Math.sin(angle);
                }});
            }}

            // Nível 1: out no semicírculo superior, in no inferior
            const level1 = nodes.filter(n => n.level === 1);
            const l1out = level1.filter(n => n.role === "out");
            const l1in  = level1.filter(n => n.role === "in");
            const R1 = radiiByLevel[1];
            if (l1out.length > 0 && l1in.length > 0) {{
                placeArc(l1out, R1, -Math.PI + 0.15, -0.15);
                placeArc(l1in,  R1,  0.15, Math.PI - 0.15);
            }} else {{
                placeArc(level1, R1, -Math.PI + 0.1, Math.PI - 0.1);
            }}

            // Níveis 2+: agrupar por pai e distribuir angularmente próximo ao pai
            for (let lv = 2; lv <= maxLevel; lv++) {{
                const levelNodes = nodes.filter(n => n.level === lv);
                if (levelNodes.length === 0) continue;
                const R = radiiByLevel[lv];

                // Mapear filhos por pai (nível anterior)
                const childrenByParent = {{}};
                links.forEach(l => {{
                    const sid = typeof l.source === "object" ? l.source.id : l.source;
                    const tid = typeof l.target === "object" ? l.target.id : l.target;
                    const sNode = nodes.find(n => n.id === sid);
                    const tNode = nodes.find(n => n.id === tid);
                    // Pai é o nó do nível anterior, filho é do nível atual
                    let parentId = null, childId = null;
                    if (sNode && sNode.level === lv - 1 && tNode && tNode.level === lv) {{
                        parentId = sid; childId = tid;
                    }} else if (tNode && tNode.level === lv - 1 && sNode && sNode.level === lv) {{
                        parentId = tid; childId = sid;
                    }}
                    if (parentId && childId) {{
                        if (!childrenByParent[parentId]) childrenByParent[parentId] = new Set();
                        childrenByParent[parentId].add(childId);
                    }}
                }});

                const parentNodes = nodes.filter(n => n.level === lv - 1 && n.px !== undefined);
                parentNodes.forEach(parent => {{
                    const children = [...(childrenByParent[parent.id] || [])]
                        .map(id => levelNodes.find(n => n.id === id)).filter(Boolean)
                        .filter(n => n.px === undefined); // só posicionar uma vez
                    if (children.length === 0) return;
                    const parentAngle = Math.atan2(parent.py - cy, parent.px - cx);
                    const spread = Math.min(Math.PI * 0.35, 0.18 * children.length);
                    children.forEach((child, i) => {{
                        const t = children.length === 1 ? 0 : (i / (children.length - 1) - 0.5);
                        const angle = parentAngle + t * spread * 2;
                        child.px = cx + R * Math.cos(angle);
                        child.py = cy + R * Math.sin(angle);
                    }});
                }});

                // Nós sem pai identificado: distribuir uniformemente no anel
                const orphans = levelNodes.filter(n => n.px === undefined);
                orphans.forEach((n, i) => {{
                    const angle = (i / Math.max(orphans.length, 1)) * 2 * Math.PI;
                    n.px = cx + R * Math.cos(angle);
                    n.py = cy + R * Math.sin(angle);
                }});
            }}

            nodes.find(n => n.role === "root").px = cx;
            nodes.find(n => n.role === "root").py = cy;

            // ── Marcadores de seta ───────────────────────────────────────
            const defs = svgEl.append("defs");

            // Gradiente suave para os anéis de fundo
            ["ring1","ring2"].forEach((id, i) => {{
                const grad = defs.append("radialGradient").attr("id", id)
                    .attr("cx","50%").attr("cy","50%").attr("r","50%");
                grad.append("stop").attr("offset","0%")
                    .attr("stop-color", i===0 ? "#636EFA" : "#AB63FA").attr("stop-opacity", 0.06);
                grad.append("stop").attr("offset","100%")
                    .attr("stop-color","transparent").attr("stop-opacity", 0);
            }});

            ["out","in","sec"].forEach((dir, i) => {{
                const colors = ["#636EFA","#2ecc71","#AB63FA"];
                defs.append("marker").attr("id",`arr-${{dir}}`)
                    .attr("viewBox","0 -4 8 8").attr("refX", 20).attr("refY", 0)
                    .attr("markerWidth", 5).attr("markerHeight", 5).attr("orient","auto")
                    .append("path").attr("d","M0,-4L8,0L0,4")
                    .attr("fill", colors[i]).attr("opacity", 0.8);
            }});

            // ── Anéis decorativos ────────────────────────────────────────
            if (level1.length > 0)
                gZoom.append("circle").attr("cx",cx).attr("cy",cy).attr("r",R1)
                    .attr("fill","none").attr("stroke","#636EFA").attr("stroke-opacity",0.1)
                    .attr("stroke-dasharray","4,4");
            const level2 = nodes.filter(n => n.level === 2);
            const R2 = radiiByLevel[2];
            if (level2.length > 0)
                gZoom.append("circle").attr("cx",cx).attr("cy",cy).attr("r",R2)
                    .attr("fill","none").attr("stroke","#AB63FA").attr("stroke-opacity",0.1)
                    .attr("stroke-dasharray","4,4");

            // ── Arestas ──────────────────────────────────────────────────
            const linkG = gZoom.append("g");
            let selectedRelationshipKey = null;
            let highlightLocked = false;
            let selectedFocusId = null;
            const linkEls = linkG.selectAll("path").data(links).enter().append("path")
                .attr("fill","none")
                .attr("stroke", d => d.direction === "out" ? "#636EFA" : d.direction === "in" ? "#2ecc71" : "#AB63FA")
                .attr("stroke-opacity", 0.45)
                .attr("stroke-width", 1.5)
                .style("pointer-events", "stroke")
                .attr("marker-end", d => {{
                    const dir = d.direction === "out" ? "out" : d.direction === "in" ? "in" : "sec";
                    return `url(#arr-${{dir}})`;
                }})
                .attr("d", d => {{
                    const sn = nodes.find(n => n.id === (typeof d.source==="object"?d.source.id:d.source));
                    const tn = nodes.find(n => n.id === (typeof d.target==="object"?d.target.id:d.target));
                    if (!sn || !tn) return "";
                    // Curva quadrática passando pelo centro para nós de mesmo anel
                    const mx = (sn.px + tn.px) / 2 * 0.6 + cx * 0.4;
                    const my = (sn.py + tn.py) / 2 * 0.6 + cy * 0.4;
                    return `M${{sn.px}},${{sn.py}} Q${{mx}},${{my}} ${{tn.px}},${{tn.py}}`;
                }});

            function relationshipKey(d) {{
                const sid = typeof d.source === "object" ? d.source.id : d.source;
                const tid = typeof d.target === "object" ? d.target.id : d.target;
                return `${{sid}}→${{tid}}|${{d.fk_name || ""}}|${{d.label || ""}}`;
            }}

            function applyPathHighlight(pathNodes) {{
                nodeEls.attr("opacity", n => pathNodes.has(n.id) ? 1 : 0.18);
                linkEls.attr("stroke-opacity", l => {{
                    const sid = typeof l.source === "object" ? l.source.id : l.source;
                    const tid = typeof l.target === "object" ? l.target.id : l.target;
                    return pathNodes.has(sid) && pathNodes.has(tid) ? 0.95 : 0.05;
                }}).attr("stroke-width", l => {{
                    const sid = typeof l.source === "object" ? l.source.id : l.source;
                    const tid = typeof l.target === "object" ? l.target.id : l.target;
                    return pathNodes.has(sid) && pathNodes.has(tid) ? 2.5 : 1.5;
                }});
            }}

            function clearPathHighlight() {{
                selectedRelationshipKey = null;
                highlightLocked = false;
                selectedFocusId = null;
                nodeEls.each(function() {{ this._fixed = false; }});
                linkEls.attr("stroke-opacity", 0.45).attr("stroke-width", 1.5);
                nodeEls.attr("opacity", 1);
            }}

            // Rótulo de coluna FK — aparece só no hover via tooltip, não poluindo o grafo
            // (guardamos no dataset do path para uso posterior)
            linkEls.each(function(d) {{ this._fkLabel = d.label; this._fkName = d.fk_name; }});

            // ── Nós ──────────────────────────────────────────────────────
            const nodeG = gZoom.append("g");
            const nodeEls = nodeG.selectAll("g").data(nodes).enter().append("g")
                .attr("transform", d => `translate(${{d.px}},${{d.py}})`)
                .attr("cursor", d => d.role !== "root" ? "pointer" : "default");

            // Sombra / glow no nó raiz
            const filt = defs.append("filter").attr("id","glow");
            filt.append("feGaussianBlur").attr("stdDeviation","4").attr("result","blur");
            const feMerge = filt.append("feMerge");
            feMerge.append("feMergeNode").attr("in","blur");
            feMerge.append("feMergeNode").attr("in","SourceGraphic");

            nodeEls.append("circle")
                .attr("r", d => nodeRadius(d))
                .attr("fill", d => nodeColor(d))
                .attr("fill-opacity", d => d.role === "root" ? 1 : 0.8)
                .attr("stroke", "#121212").attr("stroke-width", 1.5)
                .attr("filter", d => d.role === "root" ? "url(#glow)" : null);

            // Label: posicionado fora do círculo, na direção radial
            nodeEls.append("text")
                .attr("text-anchor", d => {{
                    if (d.role === "root") return "middle";
                    const angle = Math.atan2(d.py - cy, d.px - cx);
                    if (Math.abs(angle) < 0.3) return "start";
                    if (Math.abs(angle) > Math.PI - 0.3) return "end";
                    return "middle";
                }})
                .attr("dx", d => {{
                    if (d.role === "root") return 0;
                    const angle = Math.atan2(d.py - cy, d.px - cx);
                    const r = nodeRadius(d) + 6;
                    return Math.cos(angle) * r;
                }})
                .attr("dy", d => {{
                    if (d.role === "root") return 5;
                    const angle = Math.atan2(d.py - cy, d.px - cx);
                    const r = nodeRadius(d) + 6;
                    const base = Math.sin(angle) * r;
                    // Empurrar para fora quando o ângulo é próximo do eixo vertical
                    return Math.abs(Math.cos(angle)) < 0.3 ? (angle > 0 ? base + 9 : base - 3) : base + 4;
                }})
                .attr("font-size", d => d.role === "root" ? "11px" : "8px")
                .attr("font-weight", d => d.role === "root" ? "700" : "500")
                .attr("fill", d => d.role === "root" ? "#000" : "var(--text)")
                .attr("pointer-events","none")
                .text(d => d.id);

            // ── Tooltip de FK nas arestas ────────────────────────────────
            const fkTooltip = d3.select("body").append("div")
                .attr("id","graph-fk-tooltip")
                .style("position","fixed").style("pointer-events","none")
                .style("background","rgba(0,0,0,0.92)").style("border","1px solid #555")
                .style("padding","8px 12px").style("border-radius","6px")
                .style("font-size","0.75rem").style("color","#fff")
                .style("display","none").style("z-index","9000").style("max-width","260px");

            linkEls
                .on("mouseover", function(event, d) {{
                    fkTooltip.style("display","block")
                        .html(`<strong style="color:#aaa;font-size:0.65rem;">${{d.fk_name || ""}}</strong><br>${{d.label}}`);
                    if (highlightLocked || selectedRelationshipKey) return;
                    const sid = typeof d.source === "object" ? d.source.id : d.source;
                    const tid = typeof d.target === "object" ? d.target.id : d.target;
                    const sNode = nodes.find(n => n.id === sid);
                    const tNode = nodes.find(n => n.id === tid);
                    const focusId = (sNode && tNode && sNode.level > tNode.level) ? sid : tid;
                    const pathNodes = getPathToRoot(focusId);
                    nodeEls.attr("opacity", n => pathNodes.has(n.id) ? 1 : 0.18);
                    linkEls.attr("stroke-opacity", l => {{
                        const ls = typeof l.source === "object" ? l.source.id : l.source;
                        const lt = typeof l.target === "object" ? l.target.id : l.target;
                        return pathNodes.has(ls) && pathNodes.has(lt) ? 0.95 : 0.05;
                    }}).attr("stroke-width", l => {{
                        const ls = typeof l.source === "object" ? l.source.id : l.source;
                        const lt = typeof l.target === "object" ? l.target.id : l.target;
                        return pathNodes.has(ls) && pathNodes.has(lt) ? 2.5 : 1.5;
                    }});
                }})
                .on("mousemove", event => {{
                    fkTooltip.style("left", (event.clientX+14)+"px").style("top",(event.clientY-10)+"px");
                }})
                .on("mouseout", () => {{
                    fkTooltip.style("display","none");
                    if (!highlightLocked && !selectedRelationshipKey && !nodeEls.nodes().some(function() {{ return this._fixed; }})) {{
                        linkEls.attr("stroke-opacity", 0.45).attr("stroke-width", 1.5);
                        nodeEls.attr("opacity", 1);
                    }}
                }})
                .on("click", function(event, d) {{
                    event.stopPropagation();
                    const key = relationshipKey(d);
                    if (selectedRelationshipKey === key) {{
                        clearPathHighlight();
                        document.getElementById("graph-node-info").innerHTML = '<div class="graph-info-placeholder">Clique em um nó para ver detalhes</div>';
                        return;
                    }}
                    selectedRelationshipKey = key;
                    highlightLocked = true;
                    nodeEls.each(function() {{ this._fixed = true; }});
                    const sid = typeof d.source === "object" ? d.source.id : d.source;
                    const tid = typeof d.target === "object" ? d.target.id : d.target;
                    const sNode = nodes.find(n => n.id === sid);
                    const tNode = nodes.find(n => n.id === tid);
                    const focusId = (sNode && tNode && sNode.level > tNode.level) ? sid : tid;
                    selectedFocusId = focusId;
                    applyPathHighlight(getPathToRoot(focusId));
                }});

            function getPathToRoot(nodeId) {{
                const rootId = nodes.find(n => n.role === "root")?.id;
                const path = new Set([nodeId]);
                let current = nodes.find(n => n.id === nodeId);
                const guard = new Set();
                while (current && current.id !== rootId && !guard.has(current.id)) {{
                    guard.add(current.id);
                    const parent = nodes.find(candidate => candidate.level === current.level - 1 && links.some(l => {{
                        const sid = typeof l.source === "object" ? l.source.id : l.source;
                        const tid = typeof l.target === "object" ? l.target.id : l.target;
                        return (sid === candidate.id && tid === current.id) || (tid === candidate.id && sid === current.id);
                    }}));
                    if (!parent) break;
                    path.add(parent.id);
                    current = parent;
                }}
                if (rootId) path.add(rootId);
                return path;
            }}

            // ── Interação nos nós ────────────────────────────────────────
            nodeEls
                .on("mouseover", function(event, d) {{
                    // só aplica hover se não houver nó fixado
                    if (this._fixed || highlightLocked || selectedRelationshipKey) return;
                    const pathNodes = getPathToRoot(d.id);
                    linkEls.attr("stroke-opacity", l => {{
                        const sid = typeof l.source==="object"?l.source.id:l.source;
                        const tid = typeof l.target==="object"?l.target.id:l.target;
                        return pathNodes.has(sid) && pathNodes.has(tid) ? 0.95 : 0.05;
                    }}).attr("stroke-width", l => {{
                        const sid = typeof l.source==="object"?l.source.id:l.source;
                        const tid = typeof l.target==="object"?l.target.id:l.target;
                        return pathNodes.has(sid) && pathNodes.has(tid) ? 2.5 : 1.5;
                    }});
                    nodeEls.attr("opacity", n => pathNodes.has(n.id) ? 1 : 0.18);
                }})
                .on("mouseout", function() {{
                    if (this._fixed || highlightLocked || selectedRelationshipKey) return;
                    linkEls.attr("stroke-opacity", 0.45).attr("stroke-width", 1.5);
                    nodeEls.attr("opacity", 1);
                }})
                .on("click", (event, d) => {{
                    event.stopPropagation();
                    showGraphNodeInfo(d, links);
                    if (highlightLocked && selectedFocusId === d.id) {{
                        clearPathHighlight();
                        return;
                    }}
                    selectedRelationshipKey = null;
                    highlightLocked = true;
                    selectedFocusId = d.id;
                    
                    const pathNodes = getPathToRoot(d.id);

                    // Marcar todos os nós: fixar estado
                    nodeEls.each(function(n) {{ this._fixed = true; }});

                    nodeEls.attr("opacity", n => pathNodes.has(n.id) || n.role==='root' ? 1 : 0.18);
                    linkEls.attr("stroke-opacity", l => {{
                        const sid = typeof l.source==='object'?l.source.id:l.source;
                        const tid = typeof l.target==='object'?l.target.id:l.target;
                        return pathNodes.has(sid) && pathNodes.has(tid) ? 0.95 : 0.05;
                    }});
                    linkEls.attr("stroke-width", l => {{
                        const sid = typeof l.source==='object'?l.source.id:l.source;
                        const tid = typeof l.target==='object'?l.target.id:l.target;
                        return pathNodes.has(sid) && pathNodes.has(tid) ? 2.5 : 1.5;
                    }});
                }})
                .on("dblclick", (event, d) => {{
                    if (d.role !== "root") {{
                        closeGraphModal();
                        setTimeout(() => openRelationshipGraph(d.id), 100);
                    }}
                }});

            svgEl.on("click", () => {{
                document.getElementById("graph-node-info").innerHTML =
                    '<div class="graph-info-placeholder">Clique em um nó para ver detalhes</div>';
                nodeEls.each(function() {{ this._fixed = false; }});
                linkEls.attr("stroke-opacity", 0.45).attr("stroke-width", 1.5);
                nodeEls.attr("opacity", 1);
            }});

            graphSimulation = null; // layout estático, sem simulação
        }}

        function showGraphNodeInfo(d, links) {{
            const outLinks = links.filter(l => (typeof l.source==='object'?l.source.id:l.source) === d.id);
            const inLinks  = links.filter(l => (typeof l.target==='object'?l.target.id:l.target) === d.id);
            const dbData   = metadataDict[d.id] || {{}};

            const normId = d.id.includes('.') ? d.id.split('.').pop() : d.id;
            let macro = tableThemeMap[normId] || d.macro || "—";
            // t.tables pode ter "schema.tabela" ou só "tabela" — normalizar

            const allFKsOut = (dbData.foreign_keys || []).length;
            let allFKsIn = 0;
            Object.values(metadataDict).forEach(td => {{
                (td.foreign_keys || []).forEach(fk => {{
                    const ref = (fk.referred_table || "").includes('.') ? fk.referred_table.split('.').pop() : fk.referred_table;
                    if (ref === normId) allFKsIn++;
                }});
            }});

            let html = `
                <div class="graph-node-detail">
                    <div class="detail-label">Tabela</div>
                    <div class="detail-value">${{d.id}}</div>
                </div>
                <div class="graph-node-detail">
                    <div class="detail-label">Tema</div>
                    <div class="detail-value" style="font-size:0.75rem;font-weight:500;color:var(--primary)">${{macro}}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;">
                    <div class="graph-node-detail" style="margin:0">
                        <div class="detail-label">Linhas</div>
                        <div class="detail-value">${{d.row_count.toLocaleString()}}</div>
                    </div>
                    <div class="graph-node-detail" style="margin:0">
                        <div class="detail-label">Colunas</div>
                        <div class="detail-value">${{d.col_count}}</div>
                    </div>
                    <div class="graph-node-detail" style="margin:0">
                        <div class="detail-label">FK saindo</div>
                        <div class="detail-value" style="color:#636EFA">${{allFKsOut}}</div>
                    </div>
                    <div class="graph-node-detail" style="margin:0">
                        <div class="detail-label">FK entrando</div>
                        <div class="detail-value" style="color:#2ecc71">${{allFKsIn}}</div>
                    </div>
                </div>
            `;

            if (outLinks.length > 0) {{
                html += `<div style="font-size:0.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin:10px 0 5px;">Referencia no grafo (${{outLinks.length}})</div>`;
                html += `<div class="graph-fk-list">` + outLinks.map(l => {{
                    const tid = typeof l.target==='object'?l.target.id:l.target;
                    return `<div class="graph-fk-item" onclick="pushGraphLevel('${{tid}}')">
                        <span class="fk-direction fk-out">→ FK saindo</span>
                        <div class="fk-table">${{tid}}</div>
                        <div class="fk-cols">${{l.label}}</div>
                    </div>`;
                }}).join("") + `</div>`;
            }}

            if (inLinks.length > 0) {{
                html += `<div style="font-size:0.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;margin:10px 0 5px;">Referenciada por no grafo (${{inLinks.length}})</div>`;
                html += `<div class="graph-fk-list">` + inLinks.map(l => {{
                    const sid = typeof l.source==='object'?l.source.id:l.source;
                    return `<div class="graph-fk-item" onclick="pushGraphLevel('${{sid}}')">
                        <span class="fk-direction fk-in">← FK entrando</span>
                        <div class="fk-table">${{sid}}</div>
                        <div class="fk-cols">${{l.label}}</div>
                    </div>`;
                }}).join("") + `</div>`;
            }}

            html += `
                <div style="display:flex;gap:6px;margin-top:12px;">
                    <button onclick="openTableModal('${{d.id}}')"
                        style="flex:1;padding:7px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:5px;cursor:pointer;font-size:0.72rem;">
                        Ver Detalhes
                    </button>
                    ${{d.role !== 'root' ? `<button onclick="pushGraphLevel('${{d.id}}')"
                        style="flex:1;padding:7px;background:var(--primary);color:#000;border:none;border-radius:5px;cursor:pointer;font-size:0.72rem;font-weight:700;">
                        Explorar →
                    </button>` : ''}}
                </div>`;

            document.getElementById("graph-node-info").innerHTML = html;
        }}

        let graphStack = [];

        function updateGraphBreadcrumb() {{
            const title = graphStack.map((s, i) => {{
                const cls = i === graphStack.length-1 ? 'style="color:var(--primary);font-weight:700;"' : 'style="color:var(--text-muted);cursor:pointer;" onclick="popGraphTo(' + i + ')"';
                return `<span ${{cls}}>${{s.tableName}}</span>`;
            }}).join(' <span style="color:var(--border)">›</span> ');
            document.getElementById("graph-modal-title").innerHTML = title;
        }}

        function popGraphTo(idx) {{
            graphStack = graphStack.slice(0, idx + 1);
            const top = graphStack[graphStack.length - 1];
            currentGraphTable = top.tableName;
            document.getElementById("graph-node-info").innerHTML = '<div class="graph-info-placeholder">Clique em um nó para ver detalhes</div>';
            updateGraphBreadcrumb();
            renderGraph(top.tableName, currentGraphDepth);
        }}

        function pushGraphLevel(tableName) {{
            const clean = tableName.includes('.') ? tableName.split('.')[1] : tableName;
            graphStack.push({{ tableName: clean }});
            currentGraphTable = clean;
            document.getElementById("graph-node-info").innerHTML = '<div class="graph-info-placeholder">Clique em um nó para ver detalhes</div>';
            updateGraphBreadcrumb();
            renderGraph(clean, currentGraphDepth);
        }}

        function setGraphDepth(depth, btn) {{
            depth = Math.min(2, Math.max(1, depth));
            document.querySelectorAll(".depth-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentGraphDepth = depth;
            if (currentGraphTable) renderGraph(currentGraphTable, depth);
        }}

        function openRelationshipGraph(tableName) {{
            const cleanName = tableName.includes('.') ? tableName.split('.')[1] : tableName;
            currentGraphTable = cleanName;
            currentGraphDepth = 1;
            graphStack = [{{ tableName: cleanName }}];
            document.querySelectorAll(".depth-btn").forEach((b, i) => b.classList.toggle("active", i === 0));
            updateGraphBreadcrumb();
            document.getElementById("graph-node-info").innerHTML = '<div class="graph-info-placeholder">Clique em um nó para ver detalhes</div>';
            document.getElementById("graph-modal-overlay").classList.add("active");
            requestAnimationFrame(() => renderGraph(cleanName, 1));
        }}

        function closeGraphModal() {{
            document.getElementById("graph-modal-overlay").classList.remove("active");
            if (graphSimulation) {{ graphSimulation.stop(); graphSimulation = null; }}
            const tt = document.getElementById("graph-fk-tooltip");
            if (tt) tt.remove();
            graphStack = [];
        }}

        document.addEventListener("keydown", function(e) {{
            if (e.key === "Escape") {{
                if (document.getElementById("graph-modal-overlay").classList.contains("active")) {{
                    if (graphStack.length > 1) {{ graphStack.pop(); popGraphTo(graphStack.length-1); }}
                    else closeGraphModal();
                }} else {{
                    closeTableModal();
                }}
            }}
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
