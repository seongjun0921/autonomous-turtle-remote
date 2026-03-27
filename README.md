scan_publisher.py: ROS2 기반 가상 Lidar 데이터 발행 (Step 1)

260326.py: 거북이 주행 제어, MySQL 데이터 저장 및 Pandas 파싱 (Step 2-5)

.gitignore: 불필요한 설정 파일(.idea, __pycache__ 등) 제외

실행 방법
1. ROS2 브릿지 실행 (WSL) 
    ros2 launch rosbridge_server rosbridge_websocket_launch.xml
2. 시뮬레이터 실행
    ros2 run turtlesim turtlesim_node
3. Lidar 데이터 발행
   ros2 run lds_simulation talker
4. 260326코드 실
