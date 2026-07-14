/** Shared GLB preparation: flatten hierarchy, fit to physical dims, mesh pivot offsets. */

const ModelPrep = (function () {
  function meshOffsets(preset) {
    if (!preset) return { x: 0, y: 0, z: 0 };
    return {
      x: Number(preset.model_mesh_offset_x_m) || 0,
      y: Number(preset.model_mesh_offset_y_m) || 0,
      z: Number(preset.model_mesh_offset_z_m) || 0,
    };
  }

  function templateCacheKey(objectId, dims, orientation, preset) {
    const rotArr = preset && Array.isArray(preset.model_rotation_xyz) ? preset.model_rotation_xyz : [];
    const rotKey = rotArr.map((v) => Number(v).toFixed(6)).join(',');
    const scaleKey =
      preset && typeof preset.model_scale_mul === 'number' ? Number(preset.model_scale_mul).toFixed(6) : '1';
    const visualKey =
      preset && typeof preset.model_visual_scale === 'number'
        ? Number(preset.model_visual_scale).toFixed(6)
        : '1';
    const off = meshOffsets(preset);
    const meshKey = [off.x, off.y, off.z].map((v) => Number(v).toFixed(4)).join(',');
    return `${objectId}|${orientation}|r:${rotKey}|s:${scaleKey}|v:${visualKey}|m:${meshKey}|d:${dims.height_m}`;
  }

  /** Bake world transforms into geometry to remove GLB pivot/matrix ambiguity. */
  function flattenHierarchy(root) {
    const flat = new THREE.Group();
    root.updateMatrixWorld(true);
    root.traverse((node) => {
      if (!node.isMesh || !node.geometry) return;
      const geom = node.geometry.clone();
      geom.applyMatrix4(node.matrixWorld);
      const mat = Array.isArray(node.material) ? node.material[0] : node.material;
      flat.add(new THREE.Mesh(geom, mat));
    });
    flat.position.set(0, 0, 0);
    flat.rotation.set(0, 0, 0);
    flat.scale.set(1, 1, 1);
    return flat.children.length ? flat : root;
  }

  function bakeTransformsToGeometry(model) {
    model.updateMatrixWorld(true);
    model.traverse((node) => {
      if (!node.isMesh || !node.geometry) return;
      const geom = node.geometry.clone();
      geom.applyMatrix4(node.matrixWorld);
      node.geometry = geom;
      node.position.set(0, 0, 0);
      node.rotation.set(0, 0, 0);
      node.scale.set(1, 1, 1);
    });
    model.position.set(0, 0, 0);
    model.rotation.set(0, 0, 0);
    model.scale.set(1, 1, 1);
    model.updateMatrixWorld(true);
  }

  function recenterGeometryToOrigin(model) {
    const box = new THREE.Box3().setFromObject(model);
    const center = box.getCenter(new THREE.Vector3());
    model.traverse((node) => {
      if (node.isMesh && node.geometry) {
        node.geometry.translate(-center.x, -center.y, -center.z);
      }
    });
  }

  function fitToDims(model, dims, orientation) {
    bakeTransformsToGeometry(model);
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const width = Math.max(size.x, 1e-6);
    const height = Math.max(size.y, 1e-6);
    const depth = Math.max(size.z, 1e-6);

    let sx;
    let sy;
    let sz;
    if (orientation === 'top_down') {
      const s = Math.min(dims.width_m / width, dims.height_m / height);
      sx = sy = sz = s;
    } else {
      // Upright objects expose their X/Y extents to a camera facing negative Z.
      sx = dims.width_m / width;
      sy = dims.height_m / height;
      sz = (dims.depth_m || dims.width_m) / depth;
    }

    const scaleMatrix = new THREE.Matrix4().makeScale(sx, sy, sz);
    model.traverse((node) => {
      if (node.isMesh && node.geometry) {
        node.geometry.applyMatrix4(scaleMatrix);
      }
    });
    recenterGeometryToOrigin(model);
  }

  function applyVisualScale(model, preset) {
    const s =
      preset && typeof preset.model_visual_scale === 'number'
        ? Number(preset.model_visual_scale)
        : 1.0;
    if (!(s > 0) || Math.abs(s - 1.0) < 1e-9) return;
    const scaleMatrix = new THREE.Matrix4().makeScale(s, s, s);
    model.traverse((node) => {
      if (node.isMesh && node.geometry) {
        node.geometry.applyMatrix4(scaleMatrix);
      }
    });
    recenterGeometryToOrigin(model);
  }

  function prepareTemplate(cloneRoot, dims, orientation, preset) {
    const model = flattenHierarchy(cloneRoot);
    const rot = preset && preset.model_rotation_xyz;
    if (Array.isArray(rot) && rot.length === 3) {
      model.rotation.set(rot[0], rot[1], rot[2]);
      model.updateMatrixWorld(true);
    }
    fitToDims(model, dims, orientation);
    // Apply visual-only silhouette scaling after fitting the physical AABB.
    applyVisualScale(model, preset);
    return model;
  }

  function placeInstance(template, world, preset) {
    const holder = new THREE.Group();
    holder.position.set(world.x, world.y, world.z);
    const instance = template.clone(true);
    const off = meshOffsets(preset);
    instance.position.set(off.x, off.y, off.z);
    holder.add(instance);
    return holder;
  }

  function worldPoseFromProjection(proj, mountHeight) {
    const camY = Math.max(Number(mountHeight) || 0, 0.05);
    return {
      camY,
      x: Number(proj.object_offset_x_m) || 0,
      y: camY + (Number(proj.object_offset_y_m) || 0),
      z: -Math.max(Number(proj.object_distance_m) || 0.5, 0.05),
    };
  }

  return {
    meshOffsets,
    templateCacheKey,
    flattenHierarchy,
    bakeTransformsToGeometry,
    recenterGeometryToOrigin,
    fitToDims,
    applyVisualScale,
    prepareTemplate,
    placeInstance,
    worldPoseFromProjection,
  };
})();
