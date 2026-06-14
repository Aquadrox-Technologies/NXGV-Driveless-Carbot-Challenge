% MATLAB script to download and plot PID log data from RISA-bot
% Run this from MATLAB on your Windows PC.

clear; clc; close all;

%% Configuration
robot_host = 'risabot';
robot_user = 'sunrise';
remote_path = '/home/sunrise/pid_log.csv';
local_path = 'pid_log.csv';

% Default PID parameters to reconstruct P, I, D terms
% Check your src/risabot_automode/config/params.yaml or active ROS params
kp = 0.8;
ki = 0.01;
kd = 0.20;
i_max = 0.3;

%% Download data from risabot
fprintf('Retrieving PID log data from robot (%s@%s)...\n', robot_user, robot_host);
scp_cmd = sprintf('scp %s@%s:%s %s', robot_user, robot_host, remote_path, local_path);
[status, cmdout] = system(scp_cmd);

if status ~= 0
    warning('SCP transfer failed. Error output:\n%s', cmdout);
    fprintf('Attempting to use local cached copy (if it exists)...\n');
else
    fprintf('Successfully downloaded log data to: %s\n', local_path);
end

%% Load and process data
if ~exist(local_path, 'file')
    error('Log file "%s" not found. Please run the pid_logger.py script on the robot first.', local_path);
end

% Read CSV file
data = readtable(local_path);
if isempty(data) || height(data) < 2
    error('Log file contains insufficient data.');
end

% Extract variables
raw_time = data.timestamp;
time = raw_time - raw_time(1); % Relative time in seconds
error_val = data.lane_error;
linear_x = data.linear_x;
angular_z = data.angular_z;

%% Reconstruct PID terms for analysis
n = height(data);
p_term = zeros(n, 1);
i_term = zeros(n, 1);
d_term = zeros(n, 1);

integral = 0;
prev_error = 0;

for i = 1:n
    if i == 1
        dt = 0.02; % Nominal 50Hz for first step
    else
        dt = raw_time(i) - raw_time(i-1);
        if dt <= 0 || dt > 0.5
            dt = 0.02;
        end
    end
    
    err = error_val(i);
    
    % Proportional
    p_term(i) = kp * err;
    
    % Integral with anti-windup clamp
    integral = integral + err * dt;
    integral = max(-i_max, min(i_max, integral));
    i_term(i) = ki * integral;
    
    % Derivative
    if i == 1
        deriv = 0;
    else
        deriv = (err - prev_error) / dt;
    end
    prev_error = err;
    d_term(i) = kd * deriv;
end

%% Plot Results
fig = figure('Name', 'RISA-bot PID Lane Follower Diagnostics', ...
             'Units', 'Normalized', 'Position', [0.1 0.1 0.8 0.8]);
         
% Subplot 1: Lane Tracking Error
subplot(3, 1, 1);
plot(time, error_val, 'r-', 'LineWidth', 1.5);
grid on; grid minor;
title('Process Variable: Lane Tracking Error');
xlabel('Time (s)');
ylabel('Error value');
legend('Lane Error');

% Subplot 2: PID Terms & Steering Command
subplot(3, 1, 2);
plot(time, p_term, 'g-', 'LineWidth', 1.2); hold on;
plot(time, i_term, 'm-', 'LineWidth', 1.2);
plot(time, d_term, 'c-', 'LineWidth', 1.2);
plot(time, angular_z, 'b--', 'LineWidth', 1.5);
grid on; grid minor;
title('PID Controller Terms & Steering Output');
xlabel('Time (s)');
ylabel('Control Output / Value');
legend('P-Term', 'I-Term', 'D-Term', 'Total Commanded Steering', 'Location', 'best');

% Subplot 3: Speeds
subplot(3, 1, 3);
plot(time, linear_x, 'k-', 'LineWidth', 1.5);
grid on; grid minor;
title('Adaptive Forward Speed');
xlabel('Time (s)');
ylabel('Velocity (m/s)');
legend('Linear Velocity (linear.x)');

% Overall annotation
sgtitle('RISA-bot Lane Follower Control System Analysis');
