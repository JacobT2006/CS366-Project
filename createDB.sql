-- Create a new database if the user does not already have one
CREATE DATABASE IF NOT EXISTS retailInfo_db;
CREATE USER IF NOT EXISTS 'retail_app'@'localhost' IDENTIFIED BY 'retail_pass';
ALTER USER 'retail_app'@'localhost' IDENTIFIED BY 'retail_pass';
GRANT ALL PRIVILEGES ON retailInfo_db.* TO 'retail_app'@'localhost';
USE retailInfo_db;
