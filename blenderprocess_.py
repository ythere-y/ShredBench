import bpy
import os
import random
import math
import sys
import numpy as np

try:
    from PIL import Image, ImageOps
except ImportError:
    print("❌ 错误: 需要 PIL 库。请在 Blender Python 环境中运行: pip install pillow")
SOURCE_ROOT_DIR = os.path.abspath("news_textures_output")
RENDER_OUTPUT_DIR = os.path.abspath("final_renders")
RESOLUTION = (4096, 4096) 
NUM_SAMPLES = 128  
PIXELS_PER_METER = 500.0
LIGHT_ENERGY = 15000 
CRUMPLE_STRENGTH_LARGE = 0.15 
CRUMPLE_STRENGTH_SMALL = 0.02 
PAPER_THICKNESS = 0.002
PACKING_DOWNSAMPLE = 0.1
PACKING_PADDING = 30
CANVAS_GROWTH = 500

if not os.path.exists(RENDER_OUTPUT_DIR):
    os.makedirs(RENDER_OUTPUT_DIR)

def reset_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0: bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0: bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0: bpy.data.images.remove(block)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge()

def setup_render_settings():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.use_denoising = False 
    scene.cycles.samples = NUM_SAMPLES
    scene.cycles.use_adaptive_sampling = True 
    scene.render.resolution_x = RESOLUTION[0]
    scene.render.resolution_y = RESOLUTION[1]
    scene.render.filter_size = 0.8 
    
    scene.cycles.max_bounces = 32
    scene.cycles.diffuse_bounces = 8
    scene.cycles.glossy_bounces = 8
    scene.cycles.transparent_max_bounces = 128
    preferences = bpy.context.preferences
    try:
        cycles_prefs = preferences.addons['cycles'].preferences
        cycles_prefs.compute_device_type = 'CUDA' 
        cycles_prefs.get_devices()
        for device in cycles_prefs.devices: device.use = True
        scene.cycles.device = 'GPU'
    except:
        print("未检测到 GPU 或设置失败，使用 CPU")
        scene.cycles.device = 'CPU'

def create_piece_object(mask_path, tex_path, idx, location, rotation_z):
    try:
        tex_image = bpy.data.images.load(tex_path)
        mask_image = bpy.data.images.load(mask_path)
    except:
        return None
    mask_image.colorspace_settings.name = 'Non-Color'

    px_w, px_h = tex_image.size
    real_w = px_w / PIXELS_PER_METER
    real_h = px_h / PIXELS_PER_METER

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = f"Piece_{idx}"
    obj.scale = (real_w, real_h, 1.0)
    obj.rotation_euler = (0, 0, rotation_z)
    
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.subdivide(number_cuts=40) 
    bpy.ops.object.mode_set(mode='OBJECT')
    mod_solid = obj.modifiers.new(name="Thickness", type='SOLIDIFY')
    mod_solid.thickness = PAPER_THICKNESS
    
    mod_sub = obj.modifiers.new(name="Subsurf", type='SUBSURF')
    mod_sub.levels = 2
    mod_sub.render_levels = 2

    mod_wave = obj.modifiers.new(name="LargeWave", type='DISPLACE')
    tex_wave = bpy.data.textures.new(f"Tex_Wave_{idx}", type='MARBLE')
    tex_wave.noise_scale = 1.5
    mod_wave.texture = tex_wave
    mod_wave.strength = CRUMPLE_STRENGTH_LARGE

    mod_crumple = obj.modifiers.new(name="SharpCrumple", type='DISPLACE')
    tex_crumple = bpy.data.textures.new(f"Tex_Crumple_{idx}", type='MUSGRAVE')
    tex_crumple.noise_scale = 8.0
    mod_crumple.texture = tex_crumple
    mod_crumple.strength = CRUMPLE_STRENGTH_SMALL
    
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new(name=f"Mat_{idx}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex_node = nodes.new('ShaderNodeTexImage')
    tex_node.image = tex_image
    tex_node.interpolation = 'Linear' 
    mask_node = nodes.new('ShaderNodeTexImage')
    mask_node.image = mask_image
    mask_node.interpolation = 'Linear' 
    mix_color_node = nodes.new('ShaderNodeMixRGB')
    mix_color_node.blend_type = 'MULTIPLY'
    mix_color_node.inputs[0].default_value = 1.0 # Fac
    math_node = nodes.new('ShaderNodeMath')
    math_node.operation = 'GREATER_THAN'
    math_node.inputs[1].default_value = 0.90 
    
    # mask_node = nodes.new('ShaderNodeTexImage')
    # mask_node.image = mask_image
    # mask_node.interpolation = 'Linear' # Mask 边缘也要锐利
    
    # math_node = nodes.new('ShaderNodeMath')
    # math_node.operation = 'GREATER_THAN'
    # math_node.inputs[1].default_value = 0.5
    
    mix_shader = nodes.new('ShaderNodeMixShader')
    trans_bsdf = nodes.new('ShaderNodeBsdfTransparent')

    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(mask_node.outputs['Color'], math_node.inputs[0])
    links.new(math_node.outputs['Value'], mix_shader.inputs['Fac'])
    links.new(trans_bsdf.outputs['BSDF'], mix_shader.inputs[1])
    links.new(bsdf.outputs['BSDF'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output.inputs['Surface'])
    bsdf.inputs['Roughness'].default_value = 1.0 
    bsdf.inputs['Specular IOR Level'].default_value = 0.0 
    
    mat.blend_method = 'CLIP'
    obj.data.materials.append(mat)

    return obj


def load_and_process_mask_for_packing(mask_path, downsample_factor, padding_px):
    img = Image.open(mask_path).convert('L')
    angle = random.uniform(0, 360)
    img_rot = img.rotate(angle, expand=True, resample=Image.BICUBIC)
    w, h = img_rot.size
    new_w = int(w * downsample_factor)
    new_h = int(h * downsample_factor)
    img_small = img_rot.resize((new_w, new_h), Image.NEAREST)
    arr = np.array(img_small) > 128

    pad_r = int(padding_px * downsample_factor)
    if pad_r > 0:
        arr_padded = arr.copy()
        for dx in range(-pad_r, pad_r+1):
            for dy in range(-pad_r, pad_r+1):
                if dx==0 and dy==0: continue
                shifted = np.roll(arr, shift=(dy, dx), axis=(0, 1))
                arr_padded |= shifted
    else:
        arr_padded = arr
    return arr_padded, angle, (w, h)

def pixel_perfect_layout(folder_path, masks):
    pieces_data = []
    total_mask_area = 0
    for i, mask_file in enumerate(masks):
        try:
            idx = int(mask_file.split("_")[1].split(".")[0])
        except: continue
        mask_path = os.path.join(folder_path, mask_file)
        mask_arr_padded, angle_deg, rot_size_px = load_and_process_mask_for_packing(
            mask_path, PACKING_DOWNSAMPLE, PACKING_PADDING
        )
        area = np.sum(mask_arr_padded)
        total_mask_area += area
        pieces_data.append({
            'idx': idx, 'mask_file': mask_file, 'mask_arr': mask_arr_padded,
            'angle': math.radians(angle_deg), 'area': area, 'rot_size_px': rot_size_px
        })
    pieces_data.sort(key=lambda x: x['area'], reverse=True)
    estimated_side = int(math.sqrt(total_mask_area / 0.5)) 
    canvas_side = int(estimated_side * 1.5)
    max_piece_dim = max([max(p['mask_arr'].shape) for p in pieces_data])
    canvas_side = max(canvas_side, max_piece_dim * 2)
    canvas = np.zeros((canvas_side, canvas_side), dtype=bool)
    placed_objects = []
    center_y, center_x = canvas_side // 2, canvas_side // 2
    
    step = 4 
    scan_margin = int(estimated_side * 1.2) // 2
    start_y = max(0, center_y - scan_margin)
    end_y = min(canvas_side, center_y + scan_margin)
    start_x = max(0, center_x - scan_margin)
    end_x = min(canvas_side, center_x + scan_margin)

    for p in pieces_data:
        mask_arr = p['mask_arr']
        p_h, p_w = mask_arr.shape
        placed = False
        best_x, best_y = -1, -1
        min_dist_sq = float('inf')
        
        for y in range(start_y, end_y, step):
            for x in range(start_x, end_x, step):
                if y+p_h > canvas_side or x+p_w > canvas_side: continue
                curr_cy = y + p_h/2
                curr_cx = x + p_w/2
                dist_sq = (curr_cy - center_y)**2 + (curr_cx - center_x)**2
                region = canvas[y:y+p_h, x:x+p_w]
                if np.any(region & mask_arr): continue 

                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    best_x, best_y = x, y
                    placed = True
                    if dist_sq < 100: break 
            if placed and min_dist_sq < 100: break

        if not placed:
            for y in range(0, canvas_side - p_h, step*2):
                if placed: break
                for x in range(0, canvas_side - p_w, step*2):
                    region = canvas[y:y+p_h, x:x+p_w]
                    if not np.any(region & mask_arr):
                        best_x, best_y = x, y
                        placed = True
                        break
        
        if placed:
            canvas[best_y:best_y+p_h, best_x:best_x+p_w] |= mask_arr
            orig_x_px = best_x / PACKING_DOWNSAMPLE
            orig_y_px = best_y / PACKING_DOWNSAMPLE
            rot_w_px, rot_h_px = p['rot_size_px']
            world_left = orig_x_px / PIXELS_PER_METER
            world_top = -orig_y_px / PIXELS_PER_METER 
            center_obj_x = world_left + (rot_w_px / PIXELS_PER_METER) / 2.0
            center_obj_y = world_top - (rot_h_px / PIXELS_PER_METER) / 2.0
            center_obj_z = random.uniform(0.01, 0.05)
            
            tex_path = os.path.join(folder_path, f"tex_{p['idx']}.png")
            mask_path = os.path.join(folder_path, p['mask_file'])
            obj = create_piece_object(mask_path, tex_path, p['idx'], (center_obj_x, center_obj_y, center_obj_z), p['angle'])
            if obj: placed_objects.append(obj)
    return placed_objects

def auto_fit_camera(objects):
    if not objects: return
    min_x, max_x = 9999.0, -9999.0
    min_y, max_y = 9999.0, -9999.0
    for obj in objects:
        loc = obj.location
        dim = obj.dimensions
        min_x = min(min_x, loc.x - dim.x/2)
        max_x = max(max_x, loc.x + dim.x/2)
        min_y = min(min_y, loc.y - dim.y/2)
        max_y = max(max_y, loc.y + dim.y/2)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    width = max_x - min_x
    height = max_y - min_y
    margin_ratio = 1.05 
    ortho_scale = max(width, height) * margin_ratio
    
    bpy.ops.object.camera_add(location=(center_x, center_y, 20), rotation=(0, 0, 0))
    cam = bpy.context.object
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ortho_scale
    bpy.context.scene.camera = cam
    bpy.ops.object.light_add(type='AREA', location=(center_x, center_y, 15))
    light = bpy.context.object
    light.data.energy = LIGHT_ENERGY
    light.data.size = ortho_scale * 1.5 
    
    bpy.ops.mesh.primitive_plane_add(size=ortho_scale * 3, location=(center_x, center_y, -0.1))
    ground = bpy.context.object
    mat_ground = bpy.data.materials.new(name="GroundMat")
    mat_ground.use_nodes = True
    bsdf = mat_ground.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1) 
    bsdf.inputs['Roughness'].default_value = 1.0 
    ground.data.materials.append(mat_ground)

def process_single_folder(folder_path, folder_name):
    print(f"处理: {folder_name}")
    files = os.listdir(folder_path)
    masks = sorted([f for f in files if f.startswith("mask_") and f.endswith(".png")])
    if not masks: return
    reset_scene()
    setup_render_settings()
    created_objects = pixel_perfect_layout(folder_path, masks)
    if created_objects:
        auto_fit_camera(created_objects)
        output_filepath = os.path.join(RENDER_OUTPUT_DIR, f"{folder_name}.png")
        bpy.context.scene.render.filepath = output_filepath
        bpy.ops.render.render(write_still=True)
        print(f"✅ 已保存高清渲染: {output_filepath}")

def main():
    if 'PIL' not in sys.modules:
        print("请确保安装了 Pillow 库 (pip install pillow)")
        return
    print(f"=== 开始高清(4K, 无降噪)渲染 ===")
    tasks = []
    for root, dirs, files in os.walk(SOURCE_ROOT_DIR):
        if "mask_0.png" in files:
            folder_name = os.path.basename(root)
            tasks.append((root, folder_name))
    tasks.sort(key=lambda x: x[1])
    for i, (path, name) in enumerate(tasks):
        target_png = os.path.join(RENDER_OUTPUT_DIR, f"{name}.png")
        if os.path.exists(target_png):
            print(f"[{i+1}/{len(tasks)}] 跳过 {name}")
            continue
        print(f"[{i+1}/{len(tasks)}] 正在渲染: {name} ...")
        process_single_folder(path, name)
    print("\n✅ 完成")

if __name__ == "__main__":
    main()
