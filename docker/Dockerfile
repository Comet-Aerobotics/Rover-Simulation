FROM ros:humble
ENV DEBIAN_FRONTEND=noninteractive
ARG INPUT_GID=995
RUN groupadd --gid "${INPUT_GID}" input && apt-get update && apt-get install -y --no-install-recommends ros-humble-joy ros-humble-depth-image-proc python3-colcon-common-extensions && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
ENV ROS_DOMAIN_ID=0 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
CMD ["bash"]
