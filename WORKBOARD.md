# WORKBOARD.md — AeroQuantum Wind Farm Production Tasks

## Assigned Agent: Antigravity

### Active Task: Map Tile Visibility, Village Cadastre Auto-Snap, and Boundary Vertex Dots
- **Branch**: `feature/map-visibility-village-cadastre-dots`
- **Files Owned**:
  - `src/components/workflow/Screen1Site.tsx`
  - `src/services/api.ts`
  - `src/index.css`
  - `backend/app/gis/village_boundary_client.py`
  - `WORKBOARD.md`

### Objectives & Completed Enhancements:
1. **Map Tile Visibility & Zero Blank Screen Across Modes**:
   - Replaced rate-limited / blocked OpenStreetMap and connection-dropping Esri satellite tile layers with high-performance edge-cached Google Maps Hybrid (`mt{s}.google.com/vt/lyrs=y`), Roadmap (`lyrs=m`), and Terrain (`lyrs=p`) tile layers.
   - Added automated mode-change resize invalidation (`map.invalidateSize()` after 60ms and 250ms) to ensure map tiles never collapse into a solid dark navy background when toggling between Site, Radius, Lasso, Village Cadastre, or layer switchers.
2. **Village Cadastre Auto-Fetch & Real Boundary Polygon**:
   - When clicking "Village Cadastre" or searching a village/town, the application immediately queries OpenStreetMap Nominatim / Overpass cadastre for the official administrative boundary polygon.
   - Automatically synchronizes cadastral boundary coordinates, geodesic area (km²), and auto-concession radius into project state.
3. **Prominent Boundary Vertex Dots**:
   - Implemented high-contrast, prominent vertex dots (`L.circleMarker`) along the perimeter of the village boundary and concession circle.
   - Start / anchor vertex marked with an emerald ring and tooltip, with golden-yellow white-bordered markers along the entire boundary indicating "from where to where" the border extends.
4. **Mobile Layout & Lasso Toolbar Positioning**:
   - Moved the floating Lasso toolbar to the bottom (`bottom-24 md:bottom-8`) so it never overlaps or blocks the top search bar or mode tabs on mobile devices.
5. **Verification & Quality Gates**:
   - `npm run build`: PASS (0 errors, Vite production build clean in 40.5s).
   - Strictly 0 emojis in all code and UI.


