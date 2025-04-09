import streamlit as st
import osmnx as ox
import networkx as nx
import geopy.distance
import folium
from folium import plugins
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import time


# Set page configuration
st.set_page_config(page_title="A* Path Finder", page_icon="🗺️", layout="wide")


# App title and description
st.title("🗺️ A* Path Finder")
st.markdown(
    """
This application uses the A* algorithm to find the shortest path between two points.
Select your starting and ending locations, choose your mode of transport, and see the optimal route!
"""
)


# Initialize the geocoder
@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="astar_path_finder")


geocoder = get_geocoder()


# Function to search for locations
def search_location(query):
    if not query:
        return None
    try:
        location = geocoder.geocode(query)
        if location:
            return {
                "address": location.address,
                "lat": location.latitude,
                "lon": location.longitude,
            }
    except Exception as e:
        st.error(f"Error searching for location: {e}")
    return None


# Cache the graph loading to avoid repeated downloads
@st.cache_resource
def load_graph(place, network_type="walk"):
    with st.spinner(f"Loading map data for {place}..."):
        G = ox.graph_from_place(place, network_type=network_type, simplify=True)
    return G


# Function to find the shortest path using A*
def find_path(G, start_coords, goal_coords, mode):
    # Find nearest nodes
    start_node = ox.nearest_nodes(G, start_coords[1], start_coords[0])
    goal_node = ox.nearest_nodes(G, goal_coords[1], goal_coords[0])

    # Check if a path exists
    if nx.has_path(G, start_node, goal_node):
        # Find the shortest path using A* algorithm
        route = nx.astar_path(G, start_node, goal_node, weight="length")

        # Convert route nodes to coordinates
        route_coords = [(G.nodes[node]["y"], G.nodes[node]["x"]) for node in route]

        # Calculate distance
        total_distance = 0
        for i in range(1, len(route_coords)):
            total_distance += geopy.distance.distance(
                route_coords[i - 1], route_coords[i]
            ).km

        # Estimate time based on mode
        speeds = {"car": 50, "walk": 5, "bike": 15}  # km/h  # km/h  # km/h

        # Calculate estimated time
        time_hours = total_distance / speeds[mode]
        time_minutes = time_hours * 60

        return {
            "route": route_coords,
            "distance": round(total_distance, 2),
            "time_minutes": round(time_minutes),
            "success": True,
        }
    else:
        return {"success": False, "error": "No path found between these points."}


# Function to create map with the route
def create_map(start_coords, goal_coords, route_coords=None):
    # Create map centered between start and end points
    center_lat = (start_coords[0] + goal_coords[0]) / 2
    center_lon = (start_coords[1] + goal_coords[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # Add markers for start and end
    folium.Marker(
        start_coords, popup="Start", icon=folium.Icon(color="green", icon="play")
    ).add_to(m)

    folium.Marker(
        goal_coords, popup="Destination", icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)

    # Add the route if available
    if route_coords:
        folium.PolyLine(route_coords, color="blue", weight=5, opacity=0.7).add_to(m)

        # Add animated marker
        plugins.AntPath(route_coords, color="blue", weight=5).add_to(m)

    return m


# Sidebar for location inputs
st.sidebar.header("Route Settings")

# Location inputs
start_method = st.sidebar.radio(
    "Start point selection method:", ["Search by name", "Use coordinates"]
)

if start_method == "Search by name":
    start_query = st.sidebar.text_input(
        "🟢 Enter starting location:", "Ba Đình, Hanoi, Vietnam"
    )
    if start_query:
        start_location = search_location(start_query)
        if start_location:
            st.sidebar.success(f"Found: {start_location['address']}")
            start_coords = (start_location["lat"], start_location["lon"])
        else:
            st.sidebar.error("Location not found. Please try a different query.")
            start_coords = None
else:
    start_lat = st.sidebar.number_input(
        "🟢 Start Latitude:", value=21.0285, format="%.6f"
    )
    start_lon = st.sidebar.number_input(
        "🟢 Start Longitude:", value=105.8542, format="%.6f"
    )
    start_coords = (start_lat, start_lon)

end_method = st.sidebar.radio(
    "End point selection method:", ["Search by name", "Use coordinates"]
)

if end_method == "Search by name":
    end_query = st.sidebar.text_input(
        "🔴 Enter destination:", "Hoàn Kiếm Lake, Hanoi, Vietnam"
    )
    if end_query:
        end_location = search_location(end_query)
        if end_location:
            st.sidebar.success(f"Found: {end_location['address']}")
            end_coords = (end_location["lat"], end_location["lon"])
        else:
            st.sidebar.error("Location not found. Please try a different query.")
            end_coords = None
else:
    end_lat = st.sidebar.number_input("🔴 End Latitude:", value=21.0287, format="%.6f")
    end_lon = st.sidebar.number_input(
        "🔴 End Longitude:", value=105.8524, format="%.6f"
    )
    end_coords = (end_lat, end_lon)

# Transportation mode selection
mode = st.sidebar.selectbox(
    "🚗 Select mode of transport:",
    options=["car", "walk", "bike"],
    format_func=lambda x: {"car": "Car 🚗", "walk": "Walking 🚶", "bike": "Bicycle 🚲"}[
        x
    ],
)

# Area to load (default to a reasonable area)
place = st.sidebar.text_input(
    "📍 Search area (city/district):", "Ba Đình, Hanoi, Vietnam"
)

# Button to find the path
find_path_button = st.sidebar.button("Find Path", type="primary")

# Main content area
if find_path_button and start_coords and end_coords and place:
    # Load the graph
    try:
        # Determine network type based on mode
        network_type = "drive" if mode == "car" else "walk"
        G = load_graph(place, network_type)

        # Find the path
        with st.spinner("Finding optimal route..."):
            result = find_path(G, start_coords, end_coords, mode)

        if result["success"]:
            # Display the map
            col1, col2 = st.columns([3, 1])

            with col1:
                st.subheader("📍 Route Map")
                m = create_map(start_coords, end_coords, result["route"])
                folium_static(m, width=800, height=500)

            with col2:
                st.subheader("📊 Route Details")
                st.markdown(
                    f"""
                **Distance:** {result['distance']} km
                
                **Estimated Time:** {result['time_minutes']} minutes
                
                **Mode:** {mode.capitalize()}
                
                **Start:** {start_coords[0]:.6f}, {start_coords[1]:.6f}
                
                **Destination:** {end_coords[0]:.6f}, {end_coords[1]:.6f}
                """
                )

                # Calculate and display traffic conditions (simulated)
                st.subheader("🚦 Traffic Info")
                traffic_factor = 1.0
                current_hour = time.localtime().tm_hour

                # Simulate traffic conditions based on time of day
                if current_hour in [7, 8, 9, 16, 17, 18]:  # Rush hours
                    traffic_status = "Heavy"
                    traffic_factor = 1.5
                elif current_hour in [10, 11, 14, 15, 19, 20]:  # Medium traffic
                    traffic_status = "Moderate"
                    traffic_factor = 1.2
                else:  # Light traffic
                    traffic_status = "Light"
                    traffic_factor = 1.0

                adjusted_time = round(result["time_minutes"] * traffic_factor)

                st.markdown(
                    f"""
                **Current Traffic:** {traffic_status}
                
                **Adjusted Time:** {adjusted_time} minutes
                """
                )

                if mode == "car":
                    # Display a simulated fuel consumption estimate
                    fuel_consumption = round(
                        result["distance"] * 0.08, 2
                    )  # Simple estimate: 8L/100km
                    st.markdown(f"**Est. Fuel:** {fuel_consumption} liters")

        else:
            st.error(result["error"])

            # Show a map anyway with just the markers
            st.subheader("📍 Map")
            m = create_map(start_coords, end_coords)
            folium_static(m, width=1000, height=500)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.info("Try a different location or check your internet connection.")
else:
    # Show initial map or instructions
    if not find_path_button:
        st.info("👈 Enter your locations and click 'Find Path' to see the route.")

        # If coordinates are available, show a starter map
        if "start_coords" in locals() and "end_coords" in locals():
            if start_coords and end_coords:
                m = create_map(start_coords, end_coords)
                folium_static(m, width=1000, height=500)
        else:
            # Show a default map of the area
            default_coords = (21.0285, 105.8542)  # Ba Đình area
            m = folium.Map(location=default_coords, zoom_start=13)
            folium_static(m, width=1000, height=500)

# Add instructions at the bottom
with st.expander("ℹ️ How to use this app"):
    st.markdown(
        """
    1. **Enter locations**: You can search for locations by name or enter coordinates directly.
    2. **Choose transport mode**: Select how you'll be traveling (car, walking, or bicycle).
    3. **Search area**: Specify the city or district where you're planning to travel.
    4. **Find Path**: Click the button to calculate the optimal route using the A* algorithm.
    
    **About the A* Algorithm**:
    A* (pronounced "A-star") is an informed search algorithm that finds the shortest path between nodes in a graph. It uses a heuristic function to guide its search, making it more efficient than algorithms like Dijkstra's that explore all possible paths.
    
    **How the time estimation works**:
    - Car: Assumes average speed of 50 km/h
    - Walking: Assumes average speed of 5 km/h
    - Bicycle: Assumes average speed of 15 km/h
    
    Times are adjusted based on simulated traffic conditions for a more realistic estimate.
    """
    )

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Powered by A* Algorithm and OpenStreetMap")
