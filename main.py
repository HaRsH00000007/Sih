"""
VrukshaChain - Blockchain-based Ayurvedic Herb Traceability System
Main Streamlit Application
"""
import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import folium
from streamlit_folium import folium_static

# Import VrukshaChain components
from config.settings import settings
from models.schemas import (
    CollectionEvent, CollectorInfo, Coordinates, HerbSpecies, 
    QualityMetrics, ConservationStatus, HarvestSeason,
    ValidationRequest
)
from agents.orchestrator import VrukshaChainOrchestrator
from utils.logger import get_logger
from utils.helpers import format_coordinates, format_percentage, format_validation_report

# Initialize logger
logger = get_logger("streamlit_app")

# Page configuration
st.set_page_config(
    page_title="VrukshaChain - Ayurvedic Herb Traceability",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize orchestrator
@st.cache_resource
def get_orchestrator():
    """Initialize and cache the orchestrator."""
    return VrukshaChainOrchestrator()

orchestrator = get_orchestrator()

# Load sample data
@st.cache_data
def load_sample_data():
    """Load sample collection events."""
    try:
        with open('data/sample_events.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning("Sample data file not found. Using minimal demo data.")
        return []

def create_collection_event_from_dict(data: Dict[str, Any]) -> CollectionEvent:
    """Convert dictionary to CollectionEvent object."""
    # Create collector info
    collector_data = data['collector']
    collector = CollectorInfo(
        collector_id=collector_data['collector_id'],
        name=collector_data['name'],
        license_number=collector_data.get('license_number'),
        experience_years=collector_data.get('experience_years'),
        contact_info=collector_data.get('contact_info')
    )
    
    # Create coordinates
    location_data = data['location']
    location = Coordinates(
        latitude=location_data['latitude'],
        longitude=location_data['longitude'],
        accuracy=location_data.get('accuracy'),
        altitude=location_data.get('altitude')
    )
    
    # Create species info
    species_data = data['species']
    species = HerbSpecies(
        common_name=species_data['common_name'],
        scientific_name=species_data['scientific_name'],
        local_names=species_data.get('local_names', []),
        conservation_status=ConservationStatus(species_data['conservation_status']),
        harvest_seasons=[HarvestSeason(season) for season in species_data['harvest_seasons']],
        restricted_regions=species_data.get('restricted_regions', [])
    )
    
    # Create quality metrics if available
    quality_metrics = None
    if 'quality_metrics' in data and data['quality_metrics']:
        quality_data = data['quality_metrics']
        quality_metrics = QualityMetrics(
            moisture_content=quality_data.get('moisture_content'),
            ash_content=quality_data.get('ash_content'),
            visual_quality_score=quality_data.get('visual_quality_score'),
            contamination_present=quality_data.get('contamination_present'),
            notes=quality_data.get('notes')
        )
    
    # Create collection event
    return CollectionEvent(
        event_id=data['event_id'],
        timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
        collector=collector,
        location=location,
        species=species,
        quantity_kg=data['quantity_kg'],
        harvest_method=data.get('harvest_method'),
        quality_metrics=quality_metrics,
        photos=data.get('photos', []),
        weather_conditions=data.get('weather_conditions'),
        notes=data.get('notes')
    )

def create_location_map(coordinates: Coordinates, title: str = "Collection Location"):
    """Create a folium map for the collection location."""
    # Create map centered on coordinates
    m = folium.Map(
        location=[coordinates.latitude, coordinates.longitude],
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    # Add marker
    folium.Marker(
        [coordinates.latitude, coordinates.longitude],
        popup=f"{title}<br>{format_coordinates(coordinates.latitude, coordinates.longitude)}",
        tooltip="Collection Site",
        icon=folium.Icon(color="green", icon="leaf")
    ).add_to(m)
    
    # Add accuracy circle if available
    if coordinates.accuracy:
        folium.Circle(
            [coordinates.latitude, coordinates.longitude],
            radius=coordinates.accuracy,
            popup=f"GPS Accuracy: {coordinates.accuracy}m",
            color="blue",
            fill=True,
            fillOpacity=0.2
        ).add_to(m)
    
    return m

async def run_validation(collection_event: CollectionEvent, validation_types: list):
    """Run validation asynchronously."""
    try:
        result = await orchestrator.validate_collection(
            collection_event, 
            validation_types=validation_types,
            use_ai_analysis=True
        )
        return result
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        st.error(f"Validation failed: {str(e)}")
        return None

def display_validation_results(validation_result):
    """Display validation results in a structured format."""
    if not validation_result:
        st.error("No validation results to display")
        return
    
    # Overall status
    status_color = {
        "compliant": "green",
        "non_compliant": "red",
        "requires_review": "orange",
        "pending": "gray"
    }
    
    status = validation_result.overall_status.value if hasattr(validation_result.overall_status, 'value') else str(validation_result.overall_status)
    color = status_color.get(status, "gray")
    
    st.markdown(f"### Validation Results")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Overall Status", 
            status.replace("_", " ").title(),
            help="Overall compliance status"
        )
    with col2:
        st.metric(
            "Confidence Score", 
            f"{validation_result.confidence_score:.1%}",
            help="Confidence in validation results"
        )
    with col3:
        st.metric(
            "Data Sources", 
            len(validation_result.data_sources_used),
            help="Number of data sources used"
        )
    
    # Compliance summary
    st.markdown("#### Summary")
    st.info(validation_result.compliance_summary)
    
    # Warnings
    if validation_result.warnings:
        st.markdown("#### Warnings")
        for warning in validation_result.warnings:
            st.warning(warning)
    
    # Recommendations
    if validation_result.recommendations:
        st.markdown("#### Recommendations")
        for rec in validation_result.recommendations:
            st.success(f"💡 {rec}")
    
    # Next steps
    if validation_result.next_steps:
        st.markdown("#### Next Steps")
        for step in validation_result.next_steps:
            st.info(f"👉 {step}")

def main():
    """Main Streamlit application."""
    
    # Header
    st.title(" VrukshaChain")
    st.subheader("Blockchain-Based Ayurvedic Herb Traceability System")
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        ["Collection Validation", "Sample Data Explorer", "System Health", "About"]
    )
    
    if page == "Collection Validation":
        validation_page()
    elif page == "Sample Data Explorer":
        sample_data_page()
    elif page == "System Health":
        system_health_page()
    elif page == "About":
        about_page()

def validation_page():
    """Collection validation page."""
    st.header("Collection Event Validation")
    st.markdown("Validate Ayurvedic herb collection events for compliance with regulations and quality standards.")
    
    # Input method selection
    input_method = st.radio(
        "Choose input method:",
        ["Manual Entry", "Load Sample Data", "Upload JSON"]
    )
    
    collection_event = None
    
    if input_method == "Manual Entry":
        collection_event = manual_entry_form()
    elif input_method == "Load Sample Data":
        collection_event = load_sample_form()
    elif input_method == "Upload JSON":
        collection_event = upload_json_form()
    
    if collection_event:
        # Display collection event details
        st.markdown("### Collection Event Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Basic Information")
            st.write(f"**Event ID:** {collection_event.event_id}")
            st.write(f"**Species:** {collection_event.species.common_name} ({collection_event.species.scientific_name})")
            st.write(f"**Collector:** {collection_event.collector.name}")
            st.write(f"**Quantity:** {collection_event.quantity_kg} kg")
            st.write(f"**Collection Date:** {collection_event.timestamp.strftime('%Y-%m-%d %H:%M')}")
            
        with col2:
            st.markdown("#### Location")
            st.write(f"**Coordinates:** {format_coordinates(collection_event.location.latitude, collection_event.location.longitude)}")
            if collection_event.location.accuracy:
                st.write(f"**GPS Accuracy:** {collection_event.location.accuracy}m")
            
            # Show map
            location_map = create_location_map(collection_event.location)
            folium_static(location_map, width=400, height=300)
        
        # Quality metrics
        if collection_event.quality_metrics:
            st.markdown("#### Quality Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                if collection_event.quality_metrics.moisture_content:
                    st.metric("Moisture Content", f"{collection_event.quality_metrics.moisture_content}%")
            with col2:
                if collection_event.quality_metrics.ash_content:
                    st.metric("Ash Content", f"{collection_event.quality_metrics.ash_content}%")
            with col3:
                if collection_event.quality_metrics.visual_quality_score:
                    st.metric("Visual Quality", f"{collection_event.quality_metrics.visual_quality_score}/10")
        
        # Validation options
        st.markdown("### Validation Options")
        validation_types = st.multiselect(
            "Select validation types:",
            ["satellite", "regulatory", "quality"],
            default=["satellite", "regulatory", "quality"],
            help="Choose which types of validation to perform"
        )
        
        # Run validation
        if st.button("🔍 Run Validation", type="primary"):
            if validation_types:
                with st.spinner("Running validation... This may take a few moments."):
                    # Run async validation
                    validation_result = asyncio.run(run_validation(collection_event, validation_types))
                    
                    if validation_result:
                        st.session_state.validation_result = validation_result
                        display_validation_results(validation_result)
                    else:
                        st.error("Validation failed. Please check your inputs and try again.")
            else:
                st.warning("Please select at least one validation type.")
        
        # Display cached results if available
        if 'validation_result' in st.session_state:
            st.markdown("---")
            st.markdown("### Previous Validation Results")
            display_validation_results(st.session_state.validation_result)

def manual_entry_form():
    """Manual entry form for collection event."""
    st.markdown("#### Enter Collection Event Details")
    
    with st.form("manual_entry"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Basic info
            st.markdown("**Basic Information**")
            species_name = st.selectbox(
                "Species",
                list(settings.AYURVEDIC_SPECIES.keys()),
                help="Select the herb species"
            )
            quantity = st.number_input("Quantity (kg)", min_value=0.1, max_value=1000.0, value=10.0)
            collection_date = st.date_input("Collection Date", datetime.now().date())
            collection_time = st.time_input("Collection Time", datetime.now().time())
            
            # Collector info
            st.markdown("**Collector Information**")
            collector_name = st.text_input("Collector Name", "Ram Kumar")
            collector_id = st.text_input("Collector ID", "COL001")
            license_number = st.text_input("License Number (optional)", "")
        
        with col2:
            # Location
            st.markdown("**Location**")
            latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=23.2599, format="%.6f")
            longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=77.4126, format="%.6f")
            gps_accuracy = st.number_input("GPS Accuracy (m)", min_value=1.0, value=5.0)
            
            # Quality metrics
            st.markdown("**Quality Metrics (Optional)**")
            moisture_content = st.number_input("Moisture Content (%)", min_value=0.0, max_value=100.0, value=8.5)
            ash_content = st.number_input("Ash Content (%)", min_value=0.0, max_value=100.0, value=6.2)
            quality_score = st.slider("Visual Quality Score", 1, 10, 8)
        
        # Additional info
        notes = st.text_area("Additional Notes", "")
        
        submitted = st.form_submit_button("Create Collection Event")
        
        if submitted:
            # Create collection event object
            species_info = settings.AYURVEDIC_SPECIES[species_name]
            
            collection_event = CollectionEvent(
                event_id=f"VRC_{datetime.now().strftime('%Y%m%d%H%M%S')}_manual",
                timestamp=datetime.combine(collection_date, collection_time),
                collector=CollectorInfo(
                    collector_id=collector_id,
                    name=collector_name,
                    license_number=license_number if license_number else None
                ),
                location=Coordinates(
                    latitude=latitude,
                    longitude=longitude,
                    accuracy=gps_accuracy
                ),
                species=HerbSpecies(
                    common_name=species_name,
                    scientific_name=species_info["scientific_name"],
                    conservation_status=ConservationStatus(species_info["conservation_status"]),
                    harvest_seasons=[HarvestSeason(season) for season in species_info["harvest_season"]]
                ),
                quantity_kg=quantity,
                quality_metrics=QualityMetrics(
                    moisture_content=moisture_content,
                    ash_content=ash_content,
                    visual_quality_score=quality_score
                ),
                notes=notes
            )
            
            return collection_event
    
    return None

def load_sample_form():
    """Load sample data form."""
    sample_data = load_sample_data()
    
    if not sample_data:
        st.warning("No sample data available.")
        return None
    
    # Create options for selection
    options = []
    for data in sample_data:
        label = f"{data['species']['common_name']} - {data['collector']['name']} - {data['timestamp'][:10]}"
        options.append((label, data))
    
    selected = st.selectbox(
        "Select a sample collection event:",
        options,
        format_func=lambda x: x[0]
    )
    
    if selected:
        return create_collection_event_from_dict(selected[1])
    
    return None

def upload_json_form():
    """Upload JSON file form."""
    uploaded_file = st.file_uploader(
        "Upload Collection Event JSON",
        type=['json'],
        help="Upload a JSON file containing collection event data"
    )
    
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            return create_collection_event_from_dict(data)
        except Exception as e:
            st.error(f"Error parsing JSON file: {str(e)}")
    
    return None

def sample_data_page():
    """Sample data explorer page."""
    st.header("Sample Data Explorer")
    st.markdown("Explore sample collection events and their characteristics.")
    
    sample_data = load_sample_data()

    if not sample_data:
        st.warning("No sample data available.")
        return
    
    # Convert to DataFrame for analysis
    df_data = []
    for data in sample_data:
        row = {
            'Event ID': data['event_id'],
            'Species': data['species']['common_name'],
            'Scientific Name': data['species']['scientific_name'],
            'Conservation Status': data['species']['conservation_status'],
            'Collector': data['collector']['name'],
            'Quantity (kg)': data['quantity_kg'],
            'Date': data['timestamp'][:10],
            'Location': f"{data['location']['latitude']:.4f}, {data['location']['longitude']:.4f}",
            'Moisture %': data.get('quality_metrics', {}).get('moisture_content', 'N/A'),
            'Quality Score': data.get('quality_metrics', {}).get('visual_quality_score', 'N/A')
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Display data table
    st.markdown("### Collection Events Overview")
    st.dataframe(df, use_container_width=True)
    
    # Analytics
    st.markdown("### Analytics")

    
    col1, col2 = st.columns(2)
    
    with col1:
        # Species distribution
        species_counts = df['Species'].value_counts()
        fig = px.pie(
            values=species_counts.values,
            names=species_counts.index,
            title="Species Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Conservation status distribution
        conservation_counts = df['Conservation Status'].value_counts()
        fig = px.bar(
            x=conservation_counts.index,
            y=conservation_counts.values,
            title="Conservation Status Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Quality metrics analysis
    quality_data = []
    for data in sample_data:
        if 'quality_metrics' in data and data['quality_metrics']:
            quality_data.append({
                'Species': data['species']['common_name'],
                'Moisture %': data['quality_metrics'].get('moisture_content'),
                'Ash %': data['quality_metrics'].get('ash_content'),
                'Quality Score': data['quality_metrics'].get('visual_quality_score')
            })
    
    if quality_data:
        quality_df = pd.DataFrame(quality_data)
        
        st.markdown("### Quality Metrics Analysis")
        
        # Scatter plot of quality metrics
        if not quality_df.empty:
            fig = px.scatter(
                quality_df,
                x='Moisture %',
                y='Ash %',
                size='Quality Score',
                color='Species',
                title="Quality Metrics Correlation",
                hover_data=['Quality Score']
            )
            st.plotly_chart(fig, use_container_width=True)

def system_health_page():
    """System health monitoring page."""
    st.header("System Health")
    st.markdown("Monitor the health and status of VrukshaChain system components.")
    
    if st.button("Check System Health", type="primary"):
        with st.spinner("Checking system health..."):
            try:
                health_status = asyncio.run(orchestrator.get_system_health())
                
                # Overall status
                overall_status = health_status.get("overall_status", "unknown")
                status_color = {
                    "healthy": "green",
                    "degraded": "orange", 
                    "unhealthy": "red"
                }.get(overall_status, "gray")
                
                st.markdown(f"### Overall Status: :{status_color}[{overall_status.upper()}]")
                st.markdown(f"**Last Check:** {health_status.get('timestamp', 'Unknown')}")
                
                # Component status
                components = health_status.get("components", {})
                if components:
                    st.markdown("### Component Status")
                    
                    for component_name, component_info in components.items():
                        status = component_info.get("status", "unknown")
                        last_test = component_info.get("last_test", "Unknown")
                        error = component_info.get("error")
                        note = component_info.get("note")
                        
                        with st.expander(f"{component_name.replace('_', ' ').title()} - {status.upper()}"):
                            st.write(f"**Status:** {status}")
                            st.write(f"**Last Test:** {last_test}")
                            if error:
                                st.error(f"**Error:** {error}")
                            if note:
                                st.info(f"**Note:** {note}")
                
                # System info
                st.markdown("### System Information")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Application:** {settings.APP_NAME}")
                    st.info(f"**Version:** {settings.APP_VERSION}")
                with col2:
                    st.info(f"**Log Level:** {settings.LOG_LEVEL}")
                    st.info(f"**Environment:** Development")
                
            except Exception as e:
                st.error(f"Failed to check system health: {str(e)}")

def about_page():
    """About page with system information."""
    st.header("About VrukshaChain")
    
    st.markdown("""
    ### Overview
    VrukshaChain is a comprehensive blockchain-based traceability system for Ayurvedic herbs that ensures 
    authenticity, quality, and sustainable sourcing practices throughout the supply chain.
    
    ### Key Features
    - **Satellite Validation**: GPS and satellite imagery verification of collection locations
    - **Regulatory Compliance**: Automated checking against NMPB and AYUSH guidelines
    - **Quality Assurance**: Standards validation for moisture, ash content, and contamination
    - **AI-Powered Analysis**: LLM-driven compliance analysis and recommendations
    - **Real-time Insights**: Web search integration for current regulatory information
    
    ### Technology Stack
    - **Backend**: Python, FastAPI, Pydantic
    - **Blockchain**: Hyperledger Fabric (planned)
    - **AI/ML**: Groq API for LLM analysis
    - **Search**: Serper API for regulatory research
    - **Frontend**: Streamlit
    - **Geospatial**: Satellite imagery APIs, Folium mapping
    
    ### Data Sources
    - National Medicinal Plants Board (NMPB) guidelines
    - Ministry of AYUSH regulations
    - Satellite imagery from Sentinel Hub and NASA Earth
    - Conservation status from IUCN Red List
    - Quality standards from pharmacopeial references
    """)
    
    st.markdown("### System Configuration")
    
    # Display relevant configuration (non-sensitive)
    config_info = {
        "Application Name": settings.APP_NAME,
        "Version": settings.APP_VERSION,
        "Log Level": settings.LOG_LEVEL,
        "Satellite Cache Hours": settings.SATELLITE_CACHE_HOURS,
        "Regulatory Cache Hours": settings.REGULATORY_CACHE_HOURS,
        "Max Harvest Age Days": settings.MAX_HARVEST_AGE_DAYS,
        "Min Coordinate Accuracy": settings.MIN_COORDINATE_ACCURACY
    }
    
    config_df = pd.DataFrame(list(config_info.items()), columns=['Parameter', 'Value'])
    st.dataframe(config_df, use_container_width=True)
    
    st.markdown("### Supported Species")
    
    # Display supported Ayurvedic species
    species_data = []
    for common_name, info in settings.AYURVEDIC_SPECIES.items():
        species_data.append({
            'Common Name': common_name.title(),
            'Scientific Name': info['scientific_name'],
            'Conservation Status': info['conservation_status'].replace('_', ' ').title(),
            'Harvest Seasons': ', '.join(info['harvest_season'])
        })
    
    species_df = pd.DataFrame(species_data)
    st.dataframe(species_df, use_container_width=True)
    
    st.markdown("### Quality Standards")
    
    # Display quality standards
    quality_standards = []
    for param, standard in settings.QUALITY_STANDARDS.items():
        if isinstance(standard, dict):
            if 'max' in standard:
                value = f"Max: {standard['max']} {standard.get('unit', '')}"
            elif 'min' in standard:
                value = f"Min: {standard['min']} {standard.get('unit', '')}"
            else:
                value = str(standard)
        else:
            value = str(standard)
        
        quality_standards.append({
            'Parameter': param.replace('_', ' ').title(),
            'Standard': value
        })
    
    quality_df = pd.DataFrame(quality_standards)
    st.dataframe(quality_df, use_container_width=True)
    
    # API Status
    st.markdown("### API Configuration Status")
    api_status = {
        "Groq API": "✅ Configured" if settings.GROQ_API_KEY else "❌ Not Configured",
        "Serper API": "✅ Configured" if settings.SERPER_API_KEY else "❌ Not Configured"
    }
    
    for api, status in api_status.items():
        if "✅" in status:
            st.success(f"{api}: {status}")
        else:
            st.error(f"{api}: {status}")
    
    st.markdown("---")
    st.markdown("*VrukshaChain v1.0.0 - Built with Streamlit*")

if __name__ == "__main__":
    main()