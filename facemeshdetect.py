import cv2
import mediapipe as mp

class faceMeshDetection:
    
    def __init__(self, static_mode=False, maxfaces=2, detection_confident=0.5, tracking_confident=0.5):
        self.static_mode = static_mode
        self.maxfaces = maxfaces
        self.detection_confident = detection_confident
        self.tracking_confident = tracking_confident
        
        self.mpdraw = mp.solutions.drawing_utils
        self.mpmeshes = mp.solutions.face_mesh
        self.facemesh = self.mpmeshes.FaceMesh(
            static_image_mode=self.static_mode,
            max_num_faces=self.maxfaces,
            min_detection_confidence=self.detection_confident,
            min_tracking_confidence=self.tracking_confident
        )
        self.drawspec = self.mpdraw.DrawingSpec(thickness=1, circle_radius=2)

    def findfacemeshes(self, frame, draw_landmark=True):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.facemesh.process(img)
        
        faces = []
        
        if results.multi_face_landmarks:
            for facelms in results.multi_face_landmarks:
                if draw_landmark:
                    self.mpdraw.draw_landmarks(
                        frame, facelms, self.mpmeshes.FACEMESH_TESSELATION,
                        self.drawspec, self.drawspec
                    )
                face = []
                
                for idx, lm in enumerate(facelms.landmark):
                    h, w, c = frame.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    face.append([cx, cy])

                faces.append(face)

        return frame, faces