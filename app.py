
import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import re
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Criminal Intelligence Analysis System",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- THEME ----------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {background:#f5f8fc;}
[data-testid="stSidebar"] {background:#0b2744;}
[data-testid="stSidebar"] * {color:white !important;}
.block-container {padding-top:1.2rem; max-width:1500px;}
.hero {
 background:linear-gradient(135deg,#082846,#14558a);
 color:white; padding:24px 30px; border-radius:18px;
 box-shadow:0 8px 25px rgba(8,40,70,.18); margin-bottom:18px;
}
.hero h1 {margin:0;font-size:34px;}
.hero p {margin:7px 0 0;font-size:16px;opacity:.9;}
.card {
 background:white;border:1px solid #e2e8f0;border-radius:15px;
 padding:18px;box-shadow:0 4px 15px rgba(15,23,42,.05);
}
.kpi {font-size:29px;font-weight:800;color:#0b3155;}
.kpi-label {font-size:13px;color:#64748b;}
.section {font-size:22px;font-weight:800;color:#0b3155;margin:8px 0 12px;}
.badge {padding:5px 9px;border-radius:20px;background:#eaf3ff;color:#14558a;font-weight:700;}
.footer {text-align:center;color:#64748b;padding:18px;}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <div class="hero">
      <h1>🕸️ Criminal Intelligence Analysis System</h1>
      <p>AI-assisted investigative intelligence prototype • Synthetic data</p>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1,1.1,1])
    with mid:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Investigator Login")
        user = st.text_input("Username", placeholder="investigator")
        password = st.text_input("Password", type="password")
        st.caption("Demo credentials: investigator / demo123")
        if st.button("Sign In", type="primary", use_container_width=True):
            if user == "investigator" and password == "demo123":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid demo credentials.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------- DATA ----------------
@st.cache_data
def demo_data():
    entities = pd.DataFrame([
        ["P001","Aarav Mehta","Person"],["P002","Kabir Shah","Person"],
        ["P003","Riya Nair","Person"],["P004","Dev Malhotra","Person"],
        ["P005","Anaya Joshi","Person"],["P006","Vikram Rao","Person"],
        ["PH001","Phone 001","Phone"],["PH002","Phone 002","Phone"],
        ["PH003","Phone 003","Phone"],["PH004","Phone 004","Phone"],
        ["VH001","Vehicle 001","Vehicle"],["VH002","Vehicle 002","Vehicle"],
        ["VH003","Vehicle 003","Vehicle"],["LOC001","Pune","Location"],
        ["LOC002","Mumbai","Location"],["LOC003","Nashik","Location"],
        ["LOC004","Nagpur","Location"],["ORG001","Alpha Logistics","Organization"],
        ["ORG002","Metro Traders","Organization"],
        ["EM001","contact1@example.test","Email"],["EM002","contact2@example.test","Email"],
        ["EM003","contact3@example.test","Email"]
    ], columns=["entity_id","name","type"])

    rel = pd.DataFrame([
        ["P001","PH001","uses","CDR-001"],["P002","PH001","uses","CDR-002"],
        ["P001","VH001","associated_with","FIR-001"],["P003","VH001","associated_with","FIR-002"],
        ["P001","LOC001","located_at","FIR-003"],["P002","LOC001","located_at","FIR-004"],
        ["P003","ORG001","associated_with","REP-001"],["P004","ORG001","associated_with","REP-002"],
        ["P005","ORG002","associated_with","REP-003"],["P006","PH003","uses","CDR-006"],
        ["P004","PH003","uses","CDR-007"],["P006","LOC002","located_at","REP-004"],
        ["P004","LOC002","located_at","REP-005"],["P002","EM001","communicates_with","SOC-001"],
        ["P005","EM002","communicates_with","SOC-002"]
    ], columns=["source","target","relationship","evidence_id"])
    return entities, rel

entities, relationships = demo_data()

# ---------------- NLP EXTRACTION ----------------
def extract_entities(text):
    found = []
    # Phone numbers
    for x in re.findall(r'(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)', text):
        found.append(["Phone", x, "Regex"])
    # Emails
    for x in re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text):
        found.append(["Email", x, "Regex"])
    # Vehicle-like registration
    for x in re.findall(r'\b[A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{3,4}\b', text.upper()):
        found.append(["Vehicle", x, "Pattern"])
    # Money
    for x in re.findall(r'(?:₹|Rs\.?\s?)\s?[\d,]+(?:\.\d+)?', text, re.I):
        found.append(["Financial Amount", x, "Pattern"])
    # Common Indian locations for demo
    locations = ["Pune","Mumbai","Nashik","Nagpur","Delhi","Bengaluru","Hyderabad"]
    for loc in locations:
        if re.search(rf'\b{re.escape(loc)}\b', text, re.I):
            found.append(["Location", loc, "Dictionary"])
    # Simple person-name heuristic after Mr/Ms or two capitalized words
    for x in re.findall(r'\b(?:Mr\.?|Ms\.?|Mrs\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', text):
        found.append(["Person", x, "NLP heuristic"])
    for x in re.findall(r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b', text):
        if x not in [r[1] for r in found]:
            found.append(["Person", x, "NLP heuristic"])
    return pd.DataFrame(found, columns=["type","value","method"]).drop_duplicates()

def build_graph(ent, rel):
    G = nx.Graph()
    for _, r in ent.iterrows():
        G.add_node(r.entity_id, label=r.name, type=r.type)
    for _, r in rel.iterrows():
        if r.source in G and r.target in G:
            G.add_edge(r.source, r.target, relationship=r.relationship, evidence=r.evidence_id)
    return G

def graph_fig(G):
    if not G.nodes:
        return go.Figure()
    pos = nx.spring_layout(G, seed=12, k=1.0)
    ex, ey = [], []
    for u,v in G.edges():
        ex += [pos[u][0],pos[v][0],None]
        ey += [pos[u][1],pos[v][1],None]
    edge = go.Scatter(x=ex,y=ey,mode="lines",line=dict(width=1.4),hoverinfo="none")
    nx_, ny_, txt, labels = [], [], [], []
    for n,d in G.nodes(data=True):
        nx_.append(pos[n][0]); ny_.append(pos[n][1])
        labels.append(d["label"])
        txt.append(f'{d["label"]}<br>Type: {d["type"]}<br>Connections: {G.degree(n)}')
    node = go.Scatter(x=nx_,y=ny_,mode="markers+text",text=labels,
        textposition="bottom center",hovertext=txt,hoverinfo="text",
        marker=dict(size=[18+4*G.degree(n) for n in G.nodes()],line=dict(width=1)))
    fig=go.Figure([edge,node])
    fig.update_layout(height=610,margin=dict(l=5,r=5,t=5,b=5),
        showlegend=False,plot_bgcolor="white",
        xaxis=dict(visible=False),yaxis=dict(visible=False))
    return fig

G = build_graph(entities, relationships)

# ---------------- SIDEBAR ----------------
st.sidebar.title("🕸️ CIA System")
st.sidebar.caption("Hackathon Prototype • v2.0")
page = st.sidebar.radio("Navigation", [
    "Dashboard","Upload & NLP","Entities","Network Graph",
    "Relationship Explorer","Analytical Signals","Reports"
])
if st.sidebar.button("Logout"):
    st.session_state.authenticated=False
    st.rerun()
st.sidebar.divider()
st.sidebar.warning("Synthetic data only. Network prominence is not proof of wrongdoing.")

# ---------------- HEADER ----------------
st.markdown("""
<div class="hero">
<h1>AI-Powered Criminal Intelligence Analysis System</h1>
<p>Unify investigative data • Extract entities • Map relationships • Analyze network structure</p>
</div>
""", unsafe_allow_html=True)

# ---------------- DASHBOARD ----------------
if page=="Dashboard":
    st.markdown('<div class="section">Investigation Dashboard</div>',unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    for col,val,label in [(a,len(entities),"Total Entities"),(b,len(relationships),"Relationships"),
                          (c,entities.type.nunique(),"Entity Types"),(d,G.number_of_nodes(),"Network Nodes")]:
        col.markdown(f'<div class="card"><div class="kpi">{val}</div><div class="kpi-label">{label}</div></div>',unsafe_allow_html=True)
    st.write("")
    l,r=st.columns([1.7,1])
    with l:
        st.markdown("### Criminal Network Overview")
        st.plotly_chart(graph_fig(G),use_container_width=True)
    with r:
        st.markdown("### Entity Distribution")
        counts=entities.type.value_counts()
        fig=go.Figure(go.Bar(x=counts.index,y=counts.values))
        fig.update_layout(height=260,margin=dict(l=5,r=5,t=10,b=10))
        st.plotly_chart(fig,use_container_width=True)
        deg=pd.DataFrame([(G.nodes[n]["label"],G.degree(n)) for n in G],columns=["Entity","Connections"]).sort_values("Connections",ascending=False).head(6)
        st.markdown("### Most Connected")
        st.dataframe(deg,hide_index=True,use_container_width=True)

# ---------------- UPLOAD & NLP ----------------
elif page=="Upload & NLP":
    st.markdown('<div class="section">Data Upload & AI Entity Extraction</div>',unsafe_allow_html=True)
    st.info("Upload a CSV or paste investigative text. The demo extractor identifies common entity patterns and creates structured output.")
    up=st.file_uploader("Upload text/CSV",type=["txt","csv"])
    text=""
    if up:
        if up.name.lower().endswith(".txt"):
            text=up.read().decode("utf-8",errors="ignore")
        else:
            df=pd.read_csv(up)
            st.dataframe(df.head(20),hide_index=True,use_container_width=True)
            text=" ".join(df.astype(str).fillna("").agg(" ".join,axis=1).tolist())
    text=st.text_area("Investigative text",value=text,height=180,
        placeholder="Example: Mr. Aarav Mehta met Mr. Kabir Shah in Pune. Contact 9876543210 and email test@example.com. Vehicle MH12AB1234.")
    if st.button("🔎 Extract Entities",type="primary"):
        if not text.strip():
            st.warning("Enter or upload text first.")
        else:
            out=extract_entities(text)
            st.session_state["extracted"]=out
            if out.empty: st.warning("No supported demo patterns found.")
            else:
                st.success(f"Extracted {len(out)} entities.")
                st.dataframe(out,hide_index=True,use_container_width=True)
                st.download_button("Download extracted entities CSV",out.to_csv(index=False).encode(), "extracted_entities.csv","text/csv")

# ---------------- ENTITIES ----------------
elif page=="Entities":
    st.markdown('<div class="section">Entity Intelligence</div>',unsafe_allow_html=True)
    q=st.text_input("Search entities")
    types=st.multiselect("Filter types",sorted(entities.type.unique()),default=sorted(entities.type.unique()))
    df=entities[entities.type.isin(types)].copy()
    if q:
        m=df.astype(str).apply(lambda x:x.str.contains(q,case=False,na=False)).any(axis=1)
        df=df[m]
    st.dataframe(df,hide_index=True,use_container_width=True)
    if not df.empty:
        selected=st.selectbox("Open entity profile",df.entity_id)
        row=df[df.entity_id==selected].iloc[0]
        neighbors=list(G.neighbors(selected)) if selected in G else []
        x,y,z=st.columns(3)
        x.metric("Entity",row["name"]); y.metric("Type",row["type"]); z.metric("Connections",len(neighbors))
        if neighbors:
            st.markdown("### Connected Entities")
            st.dataframe(entities[entities.entity_id.isin(neighbors)],hide_index=True,use_container_width=True)

# ---------------- NETWORK ----------------
elif page=="Network Graph":
    st.markdown('<div class="section">Interactive Network Graph</div>',unsafe_allow_html=True)
    types=st.multiselect("Visible entity types",sorted(entities.type.unique()),default=sorted(entities.type.unique()))
    nodes=set(entities[entities.type.isin(types)].entity_id)
    SG=G.subgraph(nodes).copy()
    st.plotly_chart(graph_fig(SG),use_container_width=True)
    st.caption("Edges represent observed relationships in the supplied synthetic data.")
    rows=[]
    for u,v,d in SG.edges(data=True):
        rows.append([SG.nodes[u]["label"],d["relationship"],SG.nodes[v]["label"],d["evidence"]])
    st.dataframe(pd.DataFrame(rows,columns=["Source","Relationship","Target","Evidence"]),
                 hide_index=True,use_container_width=True)

# ---------------- RELATIONSHIP ----------------
elif page=="Relationship Explorer":
    st.markdown('<div class="section">Evidence-Linked Relationship Explorer</div>',unsafe_allow_html=True)
    chosen=st.multiselect("Relationship type",sorted(relationships.relationship.unique()),
                          default=sorted(relationships.relationship.unique()))
    st.dataframe(relationships[relationships.relationship.isin(chosen)],
                 hide_index=True,use_container_width=True)
    st.markdown("### Relationship Summary")
    summary=relationships.relationship.value_counts().rename_axis("Relationship").reset_index(name="Count")
    st.dataframe(summary,hide_index=True,use_container_width=True)

# ---------------- ANALYTICS ----------------
elif page=="Analytical Signals":
    st.markdown('<div class="section">Analytical Network Signals</div>',unsafe_allow_html=True)
    degree=dict(G.degree())
    between=nx.betweenness_centrality(G)
    rows=[]
    for n in G.nodes:
        rows.append([G.nodes[n]["label"],G.nodes[n]["type"],degree[n],round(between[n],4)])
    sig=pd.DataFrame(rows,columns=["Entity","Type","Connections","Betweenness"]).sort_values(
        ["Connections","Betweenness"],ascending=False)
    st.dataframe(sig,hide_index=True,use_container_width=True)
    st.info("These are descriptive graph statistics. They should be reviewed with evidence and investigator judgment.")
    comps=list(nx.connected_components(G))
    st.markdown("### Connected Communities")
    for i,c in enumerate(comps,1):
        st.write(f"**Community {i}:** "+", ".join(G.nodes[n]["label"] for n in c))

# ---------------- REPORTS ----------------
elif page=="Reports":
    st.markdown('<div class="section">Investigation Reports</div>',unsafe_allow_html=True)
    report=st.selectbox("Report type",["Investigation Summary","Entity-wise Report","Network Analysis Report","Evidence Register"])
    if report=="Investigation Summary":
        st.write(f"Synthetic case contains **{len(entities)} entities**, **{len(relationships)} relationships**, and **{G.number_of_edges()} graph edges**.")
        st.dataframe(entities.type.value_counts().rename("count").reset_index(),hide_index=True,use_container_width=True)
    elif report=="Entity-wise Report":
        out=entities.copy(); out["connections"]=out.entity_id.map(dict(G.degree())).fillna(0).astype(int)
        st.dataframe(out,hide_index=True,use_container_width=True)
    elif report=="Network Analysis Report":
        st.json({"nodes":G.number_of_nodes(),"edges":G.number_of_edges(),
                 "density":round(nx.density(G),4),
                 "connected_components":nx.number_connected_components(G)})
    else:
        st.dataframe(relationships,hide_index=True,use_container_width=True)
    csv=entities.to_csv(index=False).encode()
    st.download_button("⬇️ Download Report CSV",csv,"investigation_report.csv","text/csv")

st.markdown('<div class="footer">Criminal Intelligence Analysis System • Synthetic-data academic prototype • Built with Python + Streamlit + NetworkX + Plotly</div>',unsafe_allow_html=True)
