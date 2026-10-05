#!/usr/bin/env python3
"""
scripts/create_turbine_glb.py

Generates a realistic, lightweight, self-contained binary GLB (glTF 2.0) wind turbine model:
- Tower: 110m tapered tubular steel tower (base diameter 4.6m, top diameter 2.4m)
- Nacelle: 14m aerodynamic housing with rear radiator and aviation beacon
- Hub: 3.4m nose cone spinner
- 3 Rotor Blades: 58m aerodynamic tapered blades with red high-visibility tip bands
- Materials: Clean PBR wind turbine off-white (RAL 9010), dark grey mechanical accents, and red aviation safety tips.

Output: frontend/assets/models/wind_turbine.glb
"""

import json
import math
import struct
from pathlib import Path


def create_wind_turbine_glb(output_path: Path):
    positions = []
    normals = []
    colors = []
    indices = []

    def add_vertex(x, y, z, nx, ny, nz, r=0.94, g=0.96, b=0.98):
        positions.extend([float(x), float(y), float(z)])
        normals.extend([float(nx), float(ny), float(nz)])
        colors.extend([float(r), float(g), float(b)])
        return len(positions) // 3 - 1

    def add_triangle(i1, i2, i3):
        indices.extend([i1, i2, i3])

    def add_quad(i1, i2, i3, i4):
        # i1, i2, i3 and i1, i3, i4
        indices.extend([i1, i2, i3, i1, i3, i4])

    # Coordinate system:
    # Z is UP (matching Cesium / ENU convention)
    # Y is FORWARD (wind comes from +Y or rotor faces +Y)
    # X is LATERAL (crosswind)

    # 1. TOWER: Base at Z=0 to Z=110m
    # Tapered cylinder: R_base = 2.3m, R_top = 1.2m
    segments = 24
    z_slices = 10
    h_tower = 110.0
    r_base = 2.4
    r_top = 1.3

    tower_grid = []
    for s in range(z_slices + 1):
        frac = s / float(z_slices)
        z = frac * h_tower
        r = r_base + frac * (r_top - r_base)
        # slight tower color gradient: slight darker near foundation
        c_val = 0.90 + 0.08 * frac
        ring = []
        for i in range(segments):
            theta = 2.0 * math.pi * i / float(segments)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            nx = math.cos(theta)
            ny = math.sin(theta)
            nz = (r_base - r_top) / h_tower
            n_len = math.hypot(nx, ny, nz)
            idx = add_vertex(x, y, z, nx / n_len, ny / n_len, nz / n_len, c_val, c_val, c_val + 0.02)
            ring.append(idx)
        tower_grid.append(ring)

    for s in range(z_slices):
        for i in range(segments):
            next_i = (i + 1) % segments
            v0 = tower_grid[s][i]
            v1 = tower_grid[s][next_i]
            v2 = tower_grid[s + 1][next_i]
            v3 = tower_grid[s + 1][i]
            add_quad(v0, v1, v2, v3)

    # Tower Base Flange ring at Z=0.5m
    for i in range(segments):
        theta = 2.0 * math.pi * i / float(segments)
        next_theta = 2.0 * math.pi * ((i + 1) % segments) / float(segments)
        # flange quad
        x1, y1 = (r_base + 0.6) * math.cos(theta), (r_base + 0.6) * math.sin(theta)
        x2, y2 = (r_base + 0.6) * math.cos(next_theta), (r_base + 0.6) * math.sin(next_theta)
        x0, y0 = tower_grid[0][i], tower_grid[0][(i + 1) % segments]
        v_f1 = add_vertex(x1, y1, 0.4, 0, 0, 1, 0.35, 0.38, 0.42)
        v_f2 = add_vertex(x2, y2, 0.4, 0, 0, 1, 0.35, 0.38, 0.42)
        add_triangle(tower_grid[0][i], v_f1, v_f2)
        add_triangle(tower_grid[0][i], v_f2, tower_grid[0][(i + 1) % segments])

    # 2. NACELLE: Atop tower at Z=110m
    # Elongated streamlined body centered at Z=112m, Y extending from -8m (tail) to +4m (front hub mount)
    nacelle_z = 111.8
    nac_w = 3.6  # width (X)
    nac_h = 4.2  # height (Z)
    nac_l_rear = -8.5  # tail
    nac_l_front = 4.2  # front nose mount

    # 8 corners of main nacelle box
    def add_box(min_x, max_x, min_y, max_y, min_z, max_z, r=0.96, g=0.97, b=0.98):
        # 6 faces
        # +Z (top)
        t0 = add_vertex(min_x, min_y, max_z, 0, 0, 1, r, g, b)
        t1 = add_vertex(max_x, min_y, max_z, 0, 0, 1, r, g, b)
        t2 = add_vertex(max_x, max_y, max_z, 0, 0, 1, r, g, b)
        t3 = add_vertex(min_x, max_y, max_z, 0, 0, 1, r, g, b)
        add_quad(t0, t1, t2, t3)
        # -Z (bottom)
        b0 = add_vertex(min_x, min_y, min_z, 0, 0, -1, r * 0.7, g * 0.7, b * 0.7)
        b1 = add_vertex(min_x, max_y, min_z, 0, 0, -1, r * 0.7, g * 0.7, b * 0.7)
        b2 = add_vertex(max_x, max_y, min_z, 0, 0, -1, r * 0.7, g * 0.7, b * 0.7)
        b3 = add_vertex(max_x, min_y, min_z, 0, 0, -1, r * 0.7, g * 0.7, b * 0.7)
        add_quad(b0, b1, b2, b3)
        # +Y (front)
        f0 = add_vertex(min_x, max_y, min_z, 0, 1, 0, r, g, b)
        f1 = add_vertex(min_x, max_y, max_z, 0, 1, 0, r, g, b)
        f2 = add_vertex(max_x, max_y, max_z, 0, 1, 0, r, g, b)
        f3 = add_vertex(max_x, max_y, min_z, 0, 1, 0, r, g, b)
        add_quad(f0, f1, f2, f3)
        # -Y (rear radiator)
        r0 = add_vertex(min_x, min_y, min_z, 0, -1, 0, 0.35, 0.38, 0.42)
        r1 = add_vertex(max_x, min_y, min_z, 0, -1, 0, 0.35, 0.38, 0.42)
        r2 = add_vertex(max_x, min_y, max_z, 0, -1, 0, 0.35, 0.38, 0.42)
        r3 = add_vertex(min_x, min_y, max_z, 0, -1, 0, 0.35, 0.38, 0.42)
        add_quad(r0, r1, r2, r3)
        # +X (right)
        rx0 = add_vertex(max_x, min_y, min_z, 1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        rx1 = add_vertex(max_x, max_y, min_z, 1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        rx2 = add_vertex(max_x, max_y, max_z, 1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        rx3 = add_vertex(max_x, min_y, max_z, 1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        add_quad(rx0, rx1, rx2, rx3)
        # -X (left)
        lx0 = add_vertex(min_x, min_y, min_z, -1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        lx1 = add_vertex(min_x, min_y, max_z, -1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        lx2 = add_vertex(min_x, max_y, max_z, -1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        lx3 = add_vertex(min_x, max_y, min_z, -1, 0, 0, r * 0.9, g * 0.9, b * 0.9)
        add_quad(lx0, lx1, lx2, lx3)

    add_box(-nac_w / 2, nac_w / 2, nac_l_rear, nac_l_front, nacelle_z - nac_h / 2, nacelle_z + nac_h / 2)

    # Aviation warning beacon light on top rear of nacelle (red pulse beacon)
    beacon_z = nacelle_z + nac_h / 2 + 0.6
    add_box(-0.35, 0.35, nac_l_rear + 0.8, nac_l_rear + 1.5, nacelle_z + nac_h / 2, beacon_z, r=0.95, g=0.15, b=0.15)

    # 3. ROTOR HUB / SPINNER NOSE CONE: Centered at (0, nac_l_front + 1.5, nacelle_z)
    hub_center_y = nac_l_front + 1.2
    hub_center_z = nacelle_z
    hub_radius = 2.4
    hub_length = 3.8
    hub_segments = 20

    hub_base_ring = []
    for i in range(hub_segments):
        theta = 2.0 * math.pi * i / float(hub_segments)
        hx = hub_radius * math.cos(theta)
        hz = hub_radius * math.sin(theta)
        hy = hub_center_y
        idx = add_vertex(hx, hy, hub_center_z + hz, math.cos(theta) * 0.7, 0.4, math.sin(theta) * 0.7, 0.96, 0.97, 0.98)
        hub_base_ring.append(idx)

    # Nose tip vertex pointing forward (+Y)
    tip_idx = add_vertex(0, hub_center_y + hub_length, hub_center_z, 0, 1, 0, 1.0, 1.0, 1.0)
    for i in range(hub_segments):
        next_i = (i + 1) % hub_segments
        add_triangle(hub_base_ring[i], tip_idx, hub_base_ring[next_i])

    # 4. THREE ROTOR BLADES (Length = 58m each, separated by 120 degrees)
    # Rotor Plane is at Y = hub_center_y + 1.2
    blade_len = 58.0
    rotor_y = hub_center_y + 1.2
    blade_angles = [0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0]

    for b_idx, b_angle in enumerate(blade_angles):
        # Direction perpendicular to axis in the X-Z plane
        cos_b = math.cos(b_angle)
        sin_b = math.sin(b_angle)

        # Cross direction along chord
        chord_dx = -sin_b
        chord_dz = cos_b

        # 6 span stations from root (r=2.5m) to tip (r=58m)
        stations = [
            (2.5, 1.6, 0.8),    # root cylinder
            (10.0, 3.2, 0.9),   # max chord
            (25.0, 2.4, 0.6),   # mid span
            (42.0, 1.6, 0.4),   # outer span
            (52.0, 1.2, 0.25),  # pre-tip
            (blade_len, 0.4, 0.1), # rounded winglet tip
        ]

        station_rings = []
        for r_station, chord_w, thickness in stations:
            # Center of station
            cx = cos_b * r_station
            cz = hub_center_z + sin_b * r_station
            cy = rotor_y - (r_station / blade_len) * 1.5  # slight pre-bend / cone angle away from tower

            # Color: station > 48m has safety red tip bands
            if r_station >= 48.0 and r_station <= 53.0:
                cr, cg, cb = 0.92, 0.18, 0.18  # Red warning band 1
            elif r_station > 53.0:
                cr, cg, cb = 0.95, 0.97, 0.98  # White tip
            else:
                cr, cg, cb = 0.94, 0.96, 0.98  # Clean blade white

            # 4 vertices per station (airfoil diamond/rhombus cross-section)
            # leading edge (+Y), trailing edge (-Y), suction side (+chord), pressure side (-chord)
            v_lead = add_vertex(cx, cy + thickness * 0.5, cz, 0, 1, 0, cr, cg, cb)
            v_trail = add_vertex(cx, cy - thickness * 0.5, cz, 0, -1, 0, cr * 0.9, cg * 0.9, cb * 0.9)
            v_suc = add_vertex(cx + chord_dx * (chord_w * 0.5), cy, cz + chord_dz * (chord_w * 0.5), chord_dx, 0, chord_dz, cr, cg, cb)
            v_press = add_vertex(cx - chord_dx * (chord_w * 0.5), cy, cz - chord_dz * (chord_w * 0.5), -chord_dx, 0, -chord_dz, cr, cg, cb)

            station_rings.append((v_lead, v_suc, v_trail, v_press))

        # Stitch quad strips between consecutive stations
        for s in range(len(stations) - 1):
            r0 = station_rings[s]
            r1 = station_rings[s + 1]
            add_quad(r0[0], r0[1], r1[1], r1[0])  # upper surface
            add_quad(r0[1], r0[2], r1[2], r1[1])  # trailing upper
            add_quad(r0[2], r0[3], r1[3], r1[2])  # trailing lower
            add_quad(r0[3], r0[0], r1[0], r1[3])  # pressure lower

        # Cap blade tip
        tip_r = station_rings[-1]
        tip_center = add_vertex(
            cos_b * (blade_len + 0.5),
            rotor_y - 1.6,
            hub_center_z + sin_b * (blade_len + 0.5),
            cos_b, 0, sin_b,
            0.92, 0.18, 0.18
        )
        add_triangle(tip_r[0], tip_r[1], tip_center)
        add_triangle(tip_r[1], tip_r[2], tip_center)
        add_triangle(tip_r[2], tip_r[3], tip_center)
        add_triangle(tip_r[3], tip_r[0], tip_center)

    # Convert to binary buffers
    total_vertices = len(positions) // 3
    total_indices = len(indices)

    # Min / Max bounds
    xs = [positions[i * 3] for i in range(total_vertices)]
    ys = [positions[i * 3 + 1] for i in range(total_vertices)]
    zs = [positions[i * 3 + 2] for i in range(total_vertices)]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    # Binary packaging:
    # Buffer 0:
    # - indices: uint16 array
    # - positions: float32 array
    # - normals: float32 array
    # - colors: float32 array
    idx_bytes = struct.pack(f"<{total_indices}H", *indices)
    # 4-byte align
    while len(idx_bytes) % 4 != 0:
        idx_bytes += b"\x00"

    pos_bytes = struct.pack(f"<{len(positions)}f", *positions)
    norm_bytes = struct.pack(f"<{len(normals)}f", *normals)
    col_bytes = struct.pack(f"<{len(colors)}f", *colors)

    bin_data = idx_bytes + pos_bytes + norm_bytes + col_bytes

    idx_offset = 0
    idx_length = len(idx_bytes)

    pos_offset = idx_length
    pos_length = len(pos_bytes)

    norm_offset = pos_offset + pos_length
    norm_length = len(norm_bytes)

    col_offset = norm_offset + norm_length
    col_length = len(col_bytes)

    total_bin_length = len(bin_data)

    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "AeroQuantum-Wind Industrial Turbine Generator (Vestas V120 Spec)"
        },
        "scenes": [{"nodes": [0]}],
        "nodes": [{
            "name": "WindTurbine_120m",
            "mesh": 0
        }],
        "meshes": [{
            "name": "TurbineMesh",
            "primitives": [{
                "attributes": {
                    "POSITION": 1,
                    "NORMAL": 2,
                    "COLOR_0": 3
                },
                "indices": 0,
                "material": 0
            }]
        }],
        "materials": [{
            "name": "TurbineMaterial",
            "pbrMetallicRoughness": {
                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                "metallicFactor": 0.15,
                "roughnessFactor": 0.35
            },
            "doubleSided": True
        }],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": total_indices,
                "type": "SCALAR",
                "max": [max(indices)],
                "min": [min(indices)]
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": total_vertices,
                "type": "VEC3",
                "max": [max_x, max_y, max_z],
                "min": [min_x, min_y, min_z]
            },
            {
                "bufferView": 2,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": total_vertices,
                "type": "VEC3"
            },
            {
                "bufferView": 3,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": total_vertices,
                "type": "VEC3"
            }
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": idx_offset,
                "byteLength": total_indices * 2,
                "target": 34963  # ELEMENT_ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": pos_offset,
                "byteLength": pos_length,
                "target": 34962  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": norm_offset,
                "byteLength": norm_length,
                "target": 34962  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": col_offset,
                "byteLength": col_length,
                "target": 34962  # ARRAY_BUFFER
            }
        ],
        "buffers": [{
            "byteLength": total_bin_length
        }]
    }

    json_str = json.dumps(gltf_dict, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    # GLB Header: magic (4), version (4), length (4)
    # Chunk 0: length (4), type (4 = JSON), data (len)
    # Chunk 1: length (4), type (4 = BIN\0), data (len)
    total_glb_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)

    header = struct.pack("<4sII", b"glTF", 2, total_glb_len)
    chunk0_header = struct.pack("<I4s", len(json_bytes), b"JSON")
    chunk1_header = struct.pack("<I4s", len(bin_data), b"BIN\x00")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(header)
        f.write(chunk0_header)
        f.write(json_bytes)
        f.write(chunk1_header)
        f.write(bin_data)

    print(f"✓ Generated high-fidelity GLB model: {output_path} ({total_glb_len / 1024:.1f} KB, {total_vertices} vertices, {total_indices // 3} triangles)")


if __name__ == "__main__":
    out_file = Path("/home/hatch/workspace/goals/aeroquantum-wind-hackathon-prototype/frontend/assets/models/wind_turbine.glb")
    create_wind_turbine_glb(out_file)
