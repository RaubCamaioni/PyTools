import * as THREE from './three/three.module.js';
import { STLLoader } from './three/addons/loaders/STLLoader.js';
import { OrbitControls } from './three/addons/controls/OrbitControls.js';

class STLViewer extends HTMLElement {
    constructor() {
        super();
        this.shadow = this.attachShadow({ mode: 'open' });
        this.container = document.createElement('div');
        this.shadow.appendChild(this.container);
        this.container.style.width = '100%';
        this.container.style.height = '100%';
        this.container.style.overflow = 'hidden';
    }

    connectedCallback() {
        this.initScene();
        this.updateDimensions();
        window.addEventListener('resize', this.updateDimensions.bind(this));
    }
    
    updateDimensions() {
        const parentWidth = this.offsetWidth;
        const parentHeight = this.offsetHeight;

        // If parent width/height is set as 100%, calculate the actual pixel values
        const computedWidth = parentWidth;
        const computedHeight = parentHeight;

        // Update the container size
        this.container.style.width = `${computedWidth}px`;
        this.container.style.height = `${computedHeight}px`;

        if (this.renderer) {
            this.renderer.setSize(computedWidth, computedHeight);
            this.camera.aspect = computedWidth / computedHeight;
            this.camera.updateProjectionMatrix();
        }
    }

    static get observedAttributes() {
        return ['url'];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'url' && oldValue !== newValue) {
            this.loadSTL(newValue); // Load the new STL when the attribute changes
        }
    }

    initScene() {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
        // transparent canvas: the page behind it is black, so the model floats on the terminal background
        const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setClearColor(0x000000, 0);
        renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
        this.container.appendChild(renderer.domElement);

        scene.background = null;

        // Add light to the scene
        const light = new THREE.AmbientLight(0x404040, 2);
        scene.add(light);

        const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight1.position.set(100, 0, 100);
        scene.add(directionalLight1);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight2.position.set(-100, 0, 100);
        scene.add(directionalLight2);

        const directionalLight3 = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight3.position.set(0, -100, 100);
        scene.add(directionalLight3);

        const directionalLight4 = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight4.position.set(0, 100, 100);
        scene.add(directionalLight4);

        camera.position.y = -50;
        camera.position.z = 50;

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.25;
        controls.enableZoom = true;
        controls.screenSpacePanning = true;

        const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };

        animate();

        window.addEventListener('resize', () => {
            renderer.setSize(this.container.offsetWidth, this.container.offsetHeight);
            camera.aspect = this.container.offsetWidth / this.container.offsetHeight;
            camera.updateProjectionMatrix();
        });

        this.scene = scene;
        this.camera = camera;
        this.renderer = renderer;
        this.controls = controls;
    }

    loadSTL(url) {
        const loader = new STLLoader();
        loader.load(url, geometry => {
            // pure white model; the lights give it shading so the shape still reads
            const material = new THREE.MeshPhongMaterial({ color: 0xffffff });
            const mesh = new THREE.Mesh(geometry, material);
            this.scene.add(mesh);

            const box = new THREE.Box3().setFromObject(mesh);
            const center = new THREE.Vector3();
            box.getCenter(center);

            mesh.position.sub(center);
        });
    }
}

customElements.define('stl-viewer', STLViewer);
