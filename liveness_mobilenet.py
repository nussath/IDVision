import cv2

def check_liveness(face_img):



    blur = cv2.Laplacian(face_img, cv2.CV_64F).var()

    if blur > 30:
        return True
    else:
        return False