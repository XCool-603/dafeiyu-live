import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/GLTFLoader.js';

// Bone name mapping from motion.glb to kawaii22.glb (VRoid humanoid structure)
const boneMapping = {
  'hips_JNT': 'J_Bip_C_Hips',
  'spine_JNT': 'J_Bip_C_Spine',
  'spine1_JNT': 'J_Bip_C_Chest',
  'spine2_JNT': 'J_Bip_C_UpperChest',
  'neck_JNT': 'J_Bip_C_Neck',
  'head_JNT': 'J_Bip_C_Head',

  // Left arm
  'l_shoulder_JNT': 'J_Bip_L_Shoulder',
  'l_arm_JNT': 'J_Bip_L_UpperArm',
  'l_forearm_JNT': 'J_Bip_L_LowerArm',
  'l_hand_JNT': 'J_Bip_L_Hand',

  // Right arm
  'r_shoulder_JNT': 'J_Bip_R_Shoulder',
  'r_arm_JNT': 'J_Bip_R_UpperArm',
  'r_forearm_JNT': 'J_Bip_R_LowerArm',
  'r_hand_JNT': 'J_Bip_R_Hand',

  // Left leg
  'l_upleg_JNT': 'J_Bip_L_UpperLeg',
  'l_leg_JNT': 'J_Bip_L_LowerLeg',
  'l_foot_JNT': 'J_Bip_L_Foot',
  'l_toebase_JNT': 'J_Bip_L_ToeBase',

  // Right leg
  'r_upleg_JNT': 'J_Bip_R_UpperLeg',
  'r_leg_JNT': 'J_Bip_R_LowerLeg',
  'r_foot_JNT': 'J_Bip_R_Foot',
  'r_toebase_JNT': 'J_Bip_R_ToeBase',

  // Left fingers
  'l_handThumb1_JNT': 'J_Bip_L_Thumb1',
  'l_handThumb2_JNT': 'J_Bip_L_Thumb2',
  'l_handThumb3_JNT': 'J_Bip_L_Thumb3',
  'l_handIndex1_JNT': 'J_Bip_L_Index1',
  'l_handIndex2_JNT': 'J_Bip_L_Index2',
  'l_handIndex3_JNT': 'J_Bip_L_Index3',
  'l_handMiddle1_JNT': 'J_Bip_L_Middle1',
  'l_handMiddle2_JNT': 'J_Bip_L_Middle2',
  'l_handMiddle3_JNT': 'J_Bip_L_Middle3',
  'l_handRing1_JNT': 'J_Bip_L_Ring1',
  'l_handRing2_JNT': 'J_Bip_L_Ring2',
  'l_handRing3_JNT': 'J_Bip_L_Ring3',
  'l_handPinky1_JNT': 'J_Bip_L_Little1',
  'l_handPinky2_JNT': 'J_Bip_L_Little2',
  'l_handPinky3_JNT': 'J_Bip_L_Little3',

  // Right fingers
  'r_handThumb1_JNT': 'J_Bip_R_Thumb1',
  'r_handThumb2_JNT': 'J_Bip_R_Thumb2',
  'r_handThumb3_JNT': 'J_Bip_R_Thumb3',
  'r_handIndex1_JNT': 'J_Bip_R_Index1',
  'r_handIndex2_JNT': 'J_Bip_R_Index2',
  'r_handIndex3_JNT': 'J_Bip_R_Index3',
  'r_handMiddle1_JNT': 'J_Bip_R_Middle1',
  'r_handMiddle2_JNT': 'J_Bip_R_Middle2',
  'r_handMiddle3_JNT': 'J_Bip_R_Middle3',
  'r_handRing1_JNT': 'J_Bip_R_Ring1',
  'r_handRing2_JNT': 'J_Bip_R_Ring2',
  'r_handRing3_JNT': 'J_Bip_R_Ring3',
  'r_handPinky1_JNT': 'J_Bip_R_Little1',
  'r_handPinky2_JNT': 'J_Bip_R_Little2',
  'r_handPinky3_JNT': 'J_Bip_R_Little3'
};

function retargetAnimation(clip) {
  const newTracks = [];
  clip.tracks.forEach(track => {
    const parts = track.name.split('.');
    const boneName = parts[0];
    const property = parts.slice(1).join('.');
    if (boneMapping[boneName]) {
      const targetName = `${boneMapping[boneName]}.${property}`;
      let newTrack;
      if (track instanceof THREE.QuaternionKeyframeTrack) {
        newTrack = new THREE.QuaternionKeyframeTrack(targetName, track.times, track.values);
      } else if (track instanceof THREE.VectorKeyframeTrack) {
        newTrack = new THREE.VectorKeyframeTrack(targetName, track.times, track.values);
      } else {
        newTrack = track.clone();
        newTrack.name = targetName;
      }
      newTracks.push(newTrack);
    }
  });
  return new THREE.AnimationClip(clip.name, clip.duration, newTracks);
}

class AnimeVTuberStage {
  constructor(canvas) {
    this.canvas = canvas;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.mixer = null;
    this.clock = new THREE.Clock();
    this.model = null;
    this.headBone = null;
    this.neckBone = null;
    this.leftUpperArm = null;
    this.rightUpperArm = null;
    this.danceAction = null;
    this.isDancing = false;
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    this.partyLights = [];

    this.init();
  }

  init() {
    const width = this.canvas.clientWidth || 600;
    const height = this.canvas.clientHeight || 750;

    // 1. Scene
    this.scene = new THREE.Scene();

    // 2. Camera (framed on upper-to-full body anime character)
    this.camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 100);
    this.camera.position.set(0, 0.82, 3.45);
    this.camera.lookAt(0, 0.70, 0);

    // 3. Renderer with transparent background
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.18;

    // 4. Lighting setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    this.scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xfffaed, 2.2);
    mainLight.position.set(2, 4, 3);
    this.scene.add(mainLight);

    const rimLight = new THREE.DirectionalLight(0x7dd3fc, 1.5);
    rimLight.position.set(-2.5, 3, -2);
    this.scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0xf472b6, 0.9);
    fillLight.position.set(0, -1, 2);
    this.scene.add(fillLight);

    // 5. Party Spotlights (for dance excitement)
    const pLight1 = new THREE.PointLight(0xff007f, 0, 10);
    pLight1.position.set(2, 2, 1);
    this.scene.add(pLight1);
    this.partyLights.push(pLight1);

    const pLight2 = new THREE.PointLight(0x00f5ff, 0, 10);
    pLight2.position.set(-2, 2, 1);
    this.scene.add(pLight2);
    this.partyLights.push(pLight2);

    // 6. Mouse Listener
    window.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      this.mouse.targetX = (e.clientX - cx) / (window.innerWidth / 2);
      this.mouse.targetY = (e.clientY - cy) / (window.innerHeight / 2);
    });

    window.addEventListener('resize', () => this.onResize());

    // 7. Load Assets
    this.loadAssets();

    // 8. Start Loop
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  onResize() {
    if (!this.canvas || !this.renderer || !this.camera) return;
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (width === 0 || height === 0) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  resetToIdlePose() {
    if (!this.model) return;
    this.model.traverse(c => {
      if (c.isSkinnedMesh && c.skeleton) {
        c.skeleton.pose();
      }
    });

    // 自然可爱的少女站姿 (手臂自然下垂至身体两侧，避免生硬 T-Pose)
    if (this.leftUpperArm) {
      this.leftUpperArm.rotation.z = -1.22;
      this.leftUpperArm.rotation.x = 0.18;
      this.leftUpperArm.rotation.y = 0.08;
    }
    if (this.rightUpperArm) {
      this.rightUpperArm.rotation.z = 1.22;
      this.rightUpperArm.rotation.x = 0.18;
      this.rightUpperArm.rotation.y = -0.08;
    }
  }

  async loadAssets() {
    const loader = new GLTFLoader();

    try {
      console.log('[3D-Stage] 正在解析 3D 虚拟女孩模型...');
      const charGltf = await loader.loadAsync('/3d/kawaii22.glb');
      this.model = charGltf.scene;

      // 缩放并居中定位
      this.model.scale.set(1.32, 1.32, 1.32);
      this.model.position.set(0, -0.45, 0);

      // 获取关键骨骼
      this.model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = false;
          child.receiveShadow = false;
          if (child.material) {
            child.material.depthWrite = true;
            if (child.material.map) child.material.map.colorSpace = THREE.SRGBColorSpace;
          }
        }
        if (child.isBone) {
          if (child.name === 'J_Bip_C_Head') this.headBone = child;
          if (child.name === 'J_Bip_C_Neck') this.neckBone = child;
          if (child.name === 'J_Bip_L_UpperArm') this.leftUpperArm = child;
          if (child.name === 'J_Bip_R_UpperArm') this.rightUpperArm = child;
        }
      });

      this.scene.add(this.model);

      // 初始化骨骼姿态
      this.resetToIdlePose();

      // 创建动画混合器
      this.mixer = new THREE.AnimationMixer(this.model);

      console.log('[3D-Stage] 3D 模型加载就绪！正在加载动作数据...');

      // 加载真人动力学跳舞动作
      const danceGltf = await loader.loadAsync('/3d/motion.glb');
      if (danceGltf.animations && danceGltf.animations.length > 0) {
        const rawDanceClip = danceGltf.animations[0];
        const retargetedClip = retargetAnimation(rawDanceClip);
        this.danceAction = this.mixer.clipAction(retargetedClip);
        this.danceAction.setLoop(THREE.LoopRepeat);
        console.log('[3D-Stage] ✅ 3D 骨骼跳舞动作装载完成！通道数:', retargetedClip.tracks.length);
      }

      window.__is3DReady = true;
      if (window.on3DModelReady) window.on3DModelReady();

    } catch (err) {
      console.error('[3D-Stage] 3D 舞台加载异常:', err);
    }
  }

  playDance() {
    if (!this.mixer || !this.danceAction) {
      console.warn('[3D-Stage] 跳舞动作正在加载中...');
      return;
    }
    this.isDancing = true;
    this.danceAction.reset().fadeIn(0.35).play();

    // 点亮炫彩派对射灯
    this.partyLights.forEach(l => l.intensity = 3.8);
    console.log('[3D-Stage] 💃 3D 真实骨骼跳舞模式启动！');
  }

  stopDance() {
    if (!this.mixer || !this.danceAction || !this.isDancing) return;
    this.isDancing = false;
    this.danceAction.fadeOut(0.4);

    setTimeout(() => {
      this.resetToIdlePose();
    }, 400);

    this.partyLights.forEach(l => l.intensity = 0);
    console.log('[3D-Stage] 3D 舞蹈结束，恢复优雅待机');
  }

  animate() {
    requestAnimationFrame(this.animate);

    const delta = this.clock.getDelta();
    const elapsedTime = this.clock.getElapsedTime();

    if (this.mixer && this.isDancing) {
      this.mixer.update(delta);
    }

    // 待机状态下的自然呼吸与灵动跟随
    if (this.model && !this.isDancing) {
      // 呼吸与身体微浮动
      const breath = Math.sin(elapsedTime * 2.2) * 0.007;
      this.model.position.y = -0.45 + breath;

      // 手臂微幅随呼吸摇曳
      if (this.leftUpperArm) {
        this.leftUpperArm.rotation.z = -1.22 + Math.sin(elapsedTime * 2.2) * 0.025;
      }
      if (this.rightUpperArm) {
        this.rightUpperArm.rotation.z = 1.22 - Math.sin(elapsedTime * 2.2) * 0.025;
      }

      // 平滑插值鼠标跟随
      this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.08;
      this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.08;

      if (this.headBone) {
        this.headBone.rotation.y = THREE.MathUtils.clamp(this.mouse.x * 0.45, -0.45, 0.45);
        this.headBone.rotation.x = THREE.MathUtils.clamp(-this.mouse.y * 0.35, -0.3, 0.3);
      }
    }

    // 跳舞期间动态彩光旋转
    if (this.isDancing && this.partyLights.length >= 2) {
      const hue1 = (elapsedTime * 0.6) % 1;
      const hue2 = (elapsedTime * 0.6 + 0.5) % 1;
      this.partyLights[0].color.setHSL(hue1, 1.0, 0.6);
      this.partyLights[1].color.setHSL(hue2, 1.0, 0.6);
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}

// Global initialization
window.init3DStage = function() {
  const canvas = document.getElementById('threeStageCanvas');
  if (!canvas) {
    console.error('[3D-Stage] 找不到 #threeStageCanvas');
    return;
  }
  window.__vtuberStage = new AnimeVTuberStage(canvas);
};

window.play3DCharacterDance = function() {
  if (window.__vtuberStage) {
    window.__vtuberStage.playDance();
  }
};

window.stop3DCharacterDance = function() {
  if (window.__vtuberStage) {
    window.__vtuberStage.stopDance();
  }
};
