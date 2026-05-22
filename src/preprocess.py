import cv2 as cv
cap = cv.VideoCapture('D:\\Projects\\ShotMask\\examples\\sample.mp4')

i = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv.imwrite(f'D:\\Projects\\ShotMask\\examples\\Frames\\frame_{i:04d}.jpg', frame)
    i = i+1
    cv.imshow('Frame', frame)
    cv.waitKey(1)
    if cv.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv.destroyAllWindows()