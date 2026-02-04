import cv2
import numpy as np
import base64
import logging

logger = logging.getLogger(__name__)

# Try to import mediapipe with robust fallback
HAS_MEDIAPIPE = False
try:
    import mediapipe as mp
    try:
        # Standard import
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        HAS_MEDIAPIPE = True
        logger.info("MediaPipe solutions loaded successfully.")
    except AttributeError:
        # Some environments have issues with solutions attribute
        try:
            from mediapipe.python.solutions import hands as mp_hands
            from mediapipe.python.solutions import drawing_utils as mp_drawing
            HAS_MEDIAPIPE = True
            logger.info("MediaPipe solutions loaded via submodule.")
        except ImportError as e:
             logger.error(f"MediaPipe solutions not found: {e}")
             HAS_MEDIAPIPE = False
except ImportError as e:
    logger.error(f"MediaPipe not found: {e}")
    HAS_MEDIAPIPE = False

class GestureRecognizer:
    def __init__(self):
        self.is_ready = False
        if HAS_MEDIAPIPE:
            try:
                self.mp_hands = mp_hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=2,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.mp_draw = mp_drawing
                self.is_ready = True
                logger.info("GestureRecognizer initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing MediaPipe Hands: {e}")
                self.hands = None
        else:
            self.hands = None
            logger.warning("GestureRecognizer disabled due to missing MediaPipe.")
            
        self.finger_tips = [4, 8, 12, 16, 20] # Thumb, Index, Middle, Ring, Pinky

    def process_frame(self, base64_image: str):
        """
        Process a base64 encoded image and detect gestures.
        """
        if not self.hands:
            return None

        try:
            # Decode base64 image
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            
            image_bytes = base64.b64decode(base64_image)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None

            # Convert to RGB (MediaPipe requires RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            gestures = []
            
            if results.multi_hand_landmarks:
                for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                    # Count fingers (Robust Method)
                    fingers = []
                    
                    # Landmarks
                    # 0: Wrist
                    # 1-4: Thumb
                    # 5-8: Index
                    # 9-12: Middle
                    # 13-16: Ring
                    # 17-20: Pinky
                    
                    # Thumb
                    # For thumb, we check x-distance relative to shoulder/wrist logic or simple x comparison
                    # Better heuristic: Check angle or if tip is far from palm center compared to IP joint
                    # Simple check: Is thumb tip to the side of the MCP joint (landmark 2)
                    if handedness.classification[0].label == 'Right':
                         if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
                             fingers.append(1)
                         else:
                             fingers.append(0)
                    else:
                         if hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x:
                             fingers.append(1)
                         else:
                             fingers.append(0)

                    # Other 4 fingers
                    # Check if tip is higher than PIP joint (y-axis inverted in mediapipe)
                    # BUT hand can be rotated. 
                    # Better method: Distance from wrist (0). If Tip dist > PIP dist, it's open.
                    # Wait, MediaPipe PIP is lower index than Tip.
                    # Index: 5(MCP) -> 6(PIP) -> 7(DIP) -> 8(TIP)
                    # Folded finger: Tip is closer to wrist than PIP? Not always true if just curled a bit.
                    # Folded finger: Tip is closer to MCP than PIP is to MCP?
                    # Or simple Y check relative to local hand coordinate system.
                    
                    # Let's try a very standard heuristic that works for "Number" counting
                    # If tip is "above" the PIP joint in the Y axis (assuming hand is upright)
                    # To support rotation, we use distance to wrist.
                    # Extended: Tip is further from wrist than PIP is.
                    # Folded: Tip is closer to wrist than PIP is.
                    
                    wrist = hand_landmarks.landmark[0]
                    for id in range(1, 5): # Index to Pinky
                        tip = hand_landmarks.landmark[self.finger_tips[id]]
                        pip = hand_landmarks.landmark[self.finger_tips[id] - 2] # PIP joint (e.g. 6 for Index)
                        
                        # Calculate distance to wrist
                        dist_tip = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)**0.5
                        dist_pip = ((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2)**0.5
                        
                        # Threshold? Usually strict comparison works if fully extended/folded.
                        # But for "1" vs "2", sometimes middle finger is half curled.
                        # Let's add a small buffer or check DIP?
                        
                        # Debug logic: 1 -> 2, 2 -> 3 implies we are detecting an EXTRA finger.
                        # Maybe Thumb is false positive?
                        # Or maybe Middle/Ring are not fully curled?
                        
                        if dist_tip > dist_pip * 1.1: # Tip must be significantly further
                            fingers.append(1)
                        else:
                            fingers.append(0)
                            
                    # Fix for Thumb:
                    # 1->2 error (Index=1, but we detect Index+Thumb=2?)
                    # 2->3 error (Index+Middle=2, but we detect +Thumb=3?)
                    # It seems Thumb is always being detected as Open.
                    # Let's make Thumb check stricter.
                    # Thumb is open if tip is far from Pinky MCP (17)?
                    # Or simply check distance from Index MCP (5).
                    
                    # Refined Thumb Check:
                    # Calculate distance between Thumb Tip (4) and Pinky MCP (17).
                    # If far -> Open. If close -> Closed.
                    thumb_tip = hand_landmarks.landmark[4]
                    pinky_mcp = hand_landmarks.landmark[17]
                    index_mcp = hand_landmarks.landmark[5]
                    
                    dist_thumb_pinky = ((thumb_tip.x - pinky_mcp.x)**2 + (thumb_tip.y - pinky_mcp.y)**2)**0.5
                    dist_index_pinky = ((index_mcp.x - pinky_mcp.x)**2 + (index_mcp.y - pinky_mcp.y)**2)**0.5
                    
                    # If thumb is open, it should be far from palm (Pinky MCP is a good reference anchor)
                    # If thumb is folded over palm, it's close to Pinky MCP.
                    # Relative to hand size (Index MCP to Pinky MCP)
                    
                    # Override previous thumb check
                    if fingers:
                        fingers.pop(0) # Remove old thumb result
                    else:
                        pass # Should not happen based on logic above
                        
                    if dist_thumb_pinky > dist_index_pinky:
                        fingers.insert(0, 1)
                    else:
                        fingers.insert(0, 0)

                    total_fingers = fingers.count(1)
                    # print(f"Hand: {handedness.classification[0].label}, Fingers: {fingers}") # Debug

                    
                    # Detect specific gestures
                    gesture_name = f"Number {total_fingers}"
                    
                    # Check for "Finger Heart" (Thumb and Index crossing)
                    # Heuristic: Thumb tip and Index tip are close to each other
                    thumb_tip = hand_landmarks.landmark[4]
                    index_tip = hand_landmarks.landmark[8]
                    distance = ((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2 + (thumb_tip.z - index_tip.z)**2)**0.5
                    
                    # Threshold for "touching"
                    if distance < 0.05: 
                         # Check if other fingers are curled (optional but better)
                         if fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
                             gesture_name = "Finger Heart"

                    gestures.append(gesture_name)
                
                # Check for Two-Hand Heart
                if len(results.multi_hand_landmarks) == 2:
                    # Simple check: hands are close and forming a shape
                    # This is complex to do perfectly without specific shape matching, 
                    # but we can approximate if index fingers touch and thumbs touch
                    h1 = results.multi_hand_landmarks[0]
                    h2 = results.multi_hand_landmarks[1]
                    
                    # Check distance between index tips
                    idx_dist = ((h1.landmark[8].x - h2.landmark[8].x)**2 + (h1.landmark[8].y - h2.landmark[8].y)**2)**0.5
                    # Check distance between thumb tips
                    thumb_dist = ((h1.landmark[4].x - h2.landmark[4].x)**2 + (h1.landmark[4].y - h2.landmark[4].y)**2)**0.5
                    
                    if idx_dist < 0.1 and thumb_dist < 0.1:
                        return ["Heart Shape"]

            return gestures if gestures else None
            
        except Exception as e:
            print(f"Gesture recognition error: {e}")
            return None


