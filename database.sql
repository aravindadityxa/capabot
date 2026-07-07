-- ============================================================
-- CapaBot Database Schema
-- Database: capabot
-- Description: Skills and course recommendation data for
--              the CapaBot Resume Matcher application.
-- ============================================================

-- Create and select database
CREATE DATABASE IF NOT EXISTS capabot
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE capabot;

-- ============================================================
-- TABLE: technical_skills
-- Stores all known technical and soft skills
-- ============================================================
CREATE TABLE IF NOT EXISTS technical_skills (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    skill_name  VARCHAR(100)  NOT NULL UNIQUE,
    category    VARCHAR(50)   NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: course_recommendations
-- Stores course recommendations mapped to skills
-- ============================================================
CREATE TABLE IF NOT EXISTS course_recommendations (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    skill_name       VARCHAR(100)  NOT NULL,
    course_name      VARCHAR(200)  NOT NULL,
    course_platform  VARCHAR(100)  NOT NULL,
    course_url       VARCHAR(500)  NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (skill_name) REFERENCES technical_skills(skill_name)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- ============================================================
-- INDEX for faster skill lookups
-- ============================================================
CREATE INDEX idx_skills_category ON technical_skills(category);
CREATE INDEX idx_courses_skill   ON course_recommendations(skill_name);

