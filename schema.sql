CREATE DATABASE IF NOT EXISTS student_performance
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_performance;

-- app.py also creates these tables automatically at startup.
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(120) NOT NULL,
    class_name VARCHAR(40) NOT NULL,
    email VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    subject VARCHAR(80) NOT NULL,
    marks DECIMAL(5,2) NOT NULL,
    max_marks DECIMAL(5,2) NOT NULL DEFAULT 100,
    UNIQUE KEY unique_student_subject (student_id, subject),
    CONSTRAINT fk_marks_student FOREIGN KEY (student_id)
        REFERENCES students(id) ON DELETE CASCADE
);
