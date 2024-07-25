#!/usr/bin/env python3
import os
import sys
import csv
import rospy
import threading
import signal
import time
import copy
import numpy as np


from ros_handler import ROSHandler
from longitudinal.get_max_velocity import GetMaxVelocity
from global_path.global_path_planner import GlobalPathPlanner
import planning_handler as ph

LOCAL_PATH_LENGTH = 200

def signal_handler(sig, frame):
    sys.exit(0)

class Planning():
    def __init__(self):
        self.RH = ROSHandler()
        self.gmv = None
        self.gpp = None
        self.setting_values()

    def setting_values(self):
        self.avoid_on = True
        self.object_detected = False
        self.shutdown_event = threading.Event()

        self.specifiers = ['to_goal', 'race']
        self.race_mode = self.specifiers[0]

        # Load CSV Files
        self.to_goal_path = self.get_ref_path(self.specifiers[0])
        self.race_path = self.get_ref_path(self.specifiers[1])

        self.start_pose_initialized = False
        self.first_initialized = False
        
        self.local_action_set = []
        self.prev_lap = rospy.get_param('/now_lap')
        self.pit_point = rospy.get_param("/pit_stop_zone_coordinate")

        self.gpp = GlobalPathPlanner('KIAPI_Racing')#self.RH.map_name)
        
    def get_ref_path(self, specifier):
        toppath = os.path.dirname(os.path.realpath(__file__))
        globtraj_input_path =  toppath + "/inputs/traj_ltpl_cl/traj_ltpl_cl_" + specifier + ".csv"
        ref_path = []
        with open(globtraj_input_path, mode='r') as file:
            csv_reader = csv.DictReader(file, delimiter=';')
            for row in csv_reader:
                float_row = [float(value) for value in row.values()]
                ref_path.append(float_row)      
        return ref_path

    def check_planning_state(self):
        planning_state = 'NONE'
        race_mode = self.race_mode

        if self.first_initialized == False:
            race_mode = 'to_goal'
            planning_state = 'INIT'
        elif self.prev_lap != self.RH.lap_count and self.RH.lap_count < 5 and self.race_mode != 'pit_stop': #If pass the goal point, 
            self.start_pose_initialized = False
            self.prev_lap = self.RH.lap_count
            race_mode = 'race'
            planning_state = 'INIT'
        elif (self.RH.lap_count >= 5 or self.RH.kiapi_signal == 5 )and self.race_mode != 'pit_stop':
            self.start_pose_initialized = False
            race_mode = 'pit_stop'
            planning_state = 'INIT'
        if self.start_pose_initialized == True:
            planning_state = 'MOVE'

        return planning_state, race_mode
        
    def set_start_pos(self, race_mode):
        start_time = time.time()
        if race_mode == 'to_goal':
            global_path = copy.deepcopy(self.to_goal_path)
        elif race_mode == 'race':
            global_path = copy.deepcopy(self.race_path)
        elif race_mode == 'pit_stop':
            global_path = copy.deepcopy(self.pit_stop_path)
        # Set start pose
        idx = ph.find_closest_index(global_path, self.RH.local_pos)

        if idx is not None:
            self.start_pose_initialized = True
            self.first_initialized = True
            self.global_path = global_path
            self.now_idx = idx
            self.gmv = GetMaxVelocity(self.RH, race_mode)        
            g_path = [(float(point[0]), float(point[1])) for point in global_path]
            self.RH.publish_global_path(g_path)
            rospy.loginfo(f'[Planning] {race_mode} Start position set took {round(time.time()-start_time, 4)} sec')

    
        
    def path_update(self, trim_global_path):
        final_global_path = trim_global_path.copy()  # Make a copy of the global path to modify
        object_list = self.RH.object_list  # List of objects
        obj_radius = 15 + ( self.RH.current_velocity / 5 )  # Radius for obstacle avoidance
        
        updated_path = []
        check_object = []
        for obj in object_list:
            s, d = ph.object2frenet(trim_global_path, [obj['X'], obj['Y']])
            if -1 < d < 1:
                check_object.append(obj)


        self.RH.publish_target_object(check_object)
        self.object_detected = False
        if self.avoid_on:
            for point in trim_global_path:
                x, y = point[0], point[1]
                w_right, w_left = point[2], point[3]
                x_normvec, y_normvec = point[4], point[5]
                updated_point = point.copy()
                
                for obj in check_object:
                    obj_x, obj_y = obj['X'], obj['Y']
                    
                    if ph.distance(x, y, obj_x, obj_y) <= obj_radius:
                        self.object_detected = True
                        if w_left < 4:
                            points = np.arange(0, w_left, 1.6)
                        else:
                            points = np.arange(3.2, w_left, 1.8)

                        # 생성된 점들
                        generated_points = [(x + (-1*x_normvec) * i, y + (-1*y_normvec) * i) for i in points]

                        # 가장 가까운 점은 첫 번째 점
                        closest_point = generated_points[0]
                        updated_point[0] = closest_point[0]
                        updated_point[1] = closest_point[1]

                updated_path.append(updated_point)


            # Replace only the points in the path that need to be updated
            for i, point in enumerate(trim_global_path):
                for obj in object_list:
                    if ph.distance(point[0], point[1], obj['X'], obj['Y']) <= obj_radius:
                        final_global_path[i] = updated_path[i]

        return final_global_path

    
    
    def planning_pit_stop(self):
        start_time = time.time()
        gpp_result = self.gpp.get_shortest_path(self.RH.local_pos, self.pit_point, 'pit_stop')
        if gpp_result:
            self.pit_stop_path = self.get_ref_path('pit_stop')
            self.start_pose_initialized = False
            rospy.loginfo(f'[Planning] pit_stop Global Path set took {round(time.time()-start_time, 4)} sec')

    def initd(self):
        rate = rospy.Rate(20)
        while not rospy.is_shutdown() and not self.shutdown_event.is_set():
            planning_state, self.race_mode = self.check_planning_state()
            if planning_state == 'INIT':
                if self.race_mode == 'pit_stop':
                    self.planning_pit_stop()
                while not self.start_pose_initialized:            
                    if self.RH.local_pos is not None:
                        self.set_start_pos(self.race_mode)
                    rate.sleep()
            rate.sleep()

    def executed(self):
        rate = rospy.Rate(20)
        while not rospy.is_shutdown() and not self.shutdown_event.is_set():
            while self.first_initialized:

                #local path trim
                trimmed_path, self.global_path = ph.trim_and_update_global_path(self.global_path,self.RH.local_pos,LOCAL_PATH_LENGTH)

                #path update for obstacle
                updated_path = self.path_update(trimmed_path)

                #path spline
                interped_path, interped_kappa, interped_vel = ph.interpolate_path(updated_path)


                # Set Target Velocity
                if not self.RH.set_go:
                    local_max_vel = 0
                elif not self.start_pose_initialized:
                    local_max_vel = 10/3.6
                else:
                    max_vel =  self.gmv.get_max_velocity(self.RH.local_pos)
                    if self.object_detected:
                        local_max_vel = min(10/3.6, max_vel)
                    elif self.RH.lap_count == 0 : # 1 lap under 30 km/h 
                        local_max_vel = min(27/3.6, max_vel)
                    else:
                        local_max_vel = max_vel

                planned_vel = self.gmv.smooth_velocity_plan(interped_vel, self.RH.current_velocity, local_max_vel)

                if ( self.RH.lap_count >= 5 or self.race_mode == 'pit_stop') and len(interped_path) < 15:
                    planned_vel = -3
                else:
                    planned_vel = planned_vel[1]

                self.RH.publish2(interped_path, interped_kappa,planned_vel)

                rate.sleep()
            rate.sleep()
            

def main():
    signal.signal(signal.SIGINT, signal_handler)
    planning = Planning()
    time.sleep(0.5)

    thread1 = threading.Thread(target=planning.initd)
    thread2 = threading.Thread(target=planning.executed)

    thread1.start()
    thread2.start()

    try:
        thread1.join()
        thread2.join()

    except KeyboardInterrupt:
        planning.shutdown_event.set()
        thread1.join()
        thread2.join()
    
    rospy.loginfo("[Planning] Has shut down gracefully.")

    planning.execute()

if __name__ == "__main__":
    main()
