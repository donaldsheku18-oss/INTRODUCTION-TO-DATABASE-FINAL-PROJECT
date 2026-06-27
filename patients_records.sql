-- ====================================================================
-- Charles Ensah: DATA POPULATION & TESTING (insert_values.sql)
-- ====================================================================

-- 1. Insert Base Table Data
INSERT INTO PATIENT (Full_Name, Date_of_Birth, Gender, Phone_Number, Address, Emergency_Contact, Date_Registered) VALUES
('Charles Ensah','2007-03-12','Male','076328592','Freetown','76010111','2025-01-05'),
('Fatmata Sesay','1992-07-21','Female','076000112','Bo','76010112','2025-01-06'),
('Abdul Koroma','1978-11-09','Male','076000113','Kenema','76010113','2025-01-07'),
('Hawa Bangura','2000-01-15','Female','076000114','Makeni','76010114','2025-01-08'),
('Alhaji Kallon','1968-09-30','Male','076000115','Koidu','76010115','2025-01-09'),
('Mariama Turay','1995-06-18','Female','076000116','Port Loko','76010116','2025-01-10'),
('Ibrahim Conteh','1989-12-01','Male','O76000117','Magburaka','76010117','2025-01-11'),
('Adama Jalloh','2001-04-25','Female','076000118','Kabala','76010118','2025-01-12'),
('Sorie Fofanah','1975-08-13','Male','076000119','Moyamba','76010119','2025-01-13'),
('Isatu Mansaray','1998-02-28','Female','076000120','Freetown','76010120','2024-01-09');

INSERT INTO Health_Workers (Health_Worker_ID, Full_Name, Specialization, Role, Salary) VALUES
(1,'Lisa Wurie','General Medicine','Doctor',25000),
(2,'Fatmata Kamara','Cardiology','Doctor',32000),
(3,'Abdul Sesay','Pediatrics','Doctor',28000),
(4,'Hawa Koroma','Dermatology','Doctor',27000),
(5,'Ibrahim Turay','Orthopedics','Doctor',30000),
(6,'Mariama Conteh','Nursing','Nurse',12000),
(7,'Sorie Kallon','Nursing','Nurse',12000),
(8,'Adama Jalloh','Pharmacy','Pharmacist',15000),
(9,'Alusine Fofanah','Laboratory','Technician',10000),
(10,'Isatu Mansaray','Radiology','Technician',11000);

INSERT INTO INVENTORY (Inventory_ID, Item_Name, Unit_Cost, Quantity_Available) VALUES
(1,'Amlodipine Tablets',15.00,500),
(2,'Nitroglycerin Tablets',20.00,200),
(3,'Oseltamivir Capsules',30.00,150),
(4,'Hydrocortisone Cream',18.00,120),
(5,'Physiotherapy Equipment',1500.00,20),
(6,'Ibuprofen Tablets',10.00,600),
(7,'Metformin Tablets',12.00,400),
(8,'Vitamin C Tablets',5.00,1000),
(9,'Diclofenac Tablets',11.00,300),
(10,'Antihistamine Tablets',8.00,350);

INSERT INTO users (User_ID, Username, Passwords, Role) VALUES
(905005922, 'Donald Sheku', '@Group1', 'Admin'),
(905006142, 'Charles Ensah', '@Group1', 'Receptionist'),
(905005935, 'Lisa Wurie', '@Group1', 'Doctor');

-- 2. Insert Dependent Table Data
INSERT INTO APPOINTMENT (Appointment_ID, Appointment_Date, Patient_ID, Health_Worker_ID) VALUES
(1, '2026-06-23 10:00:00', 1, 1),
(2, '2026-02-02 09:30:00', 2, 2),
(3, '2026-02-03 11:00:00', 3, 3),
(4, '2026-02-04 12:00:00', 4, 4),
(5, '2026-02-05 10:00:00', 5, 5),
(6, '2026-02-06 11:30:00', 6, 1),
(7, '2026-02-07 12:00:00', 7, 2),
(8, '2026-02-08 01:00:00', 8, 3),
(9, '2026-02-09 08:00:00', 9, 4),
(10, '2026-02-10 09:30:00', 10, 5);

INSERT INTO PAYMENT (Payment_ID, Payment_Method, Amount, Payment_Date, Patient_ID) VALUES
(1,'Cash',250.00,'2025-02-01',1),
(2,'Orange Money',400.00,'2025-02-02',2),
(3,'Afrimoney',650.00,'2025-02-03',3),
(4,'Cash',300.00,'2025-02-04',4),
(5,'Bank Transfer',1200.00,'2025-02-05',5),
(6,'Orange Money',200.00,'2025-02-06',6),
(10,'Cash',180.00,'2025-02-10',10);

INSERT INTO VISITATION (Visitation_ID, Visit_Date, Reason, Patient_ID) VALUES
(1,'2026-02-01','Routine Checkup',1),
(2,'2026-02-02','Chest Pain',2),
(3,'2026-02-03','Fever',3),
(4,'2026-02-04','Skin Rash',4),
(5,'2026-02-05','Back Pain',5),
(6,'2026-02-06','Headache',6),
(7,'2026-02-07','Follow Up',7),
(8,'2026-02-08','Flu Symptoms',8),
(9,'2026-02-09','Joint Pain',9),
(10,'2026-02-10','Allergy',10);

INSERT INTO DIAGNOSIS (Diagnosis_ID, Patient_ID, Diagnosis_Name, Description, Visitation_ID) VALUES
(1,1,'Hypertension','Elevated blood pressure',1),
(2,2,'Angina','Reduced blood flow to heart',2),
(3,3,'Influenza','Viral infection',3),
(4,4,'Dermatitis','Skin inflammation',4),
(5,5,'Lower Back Strain','Muscle strain',5),
(6,6,'Migraine','Recurring headache',6),
(7,7,'Type 2 Diabetes','High blood sugar',7),
(8,8,'Common Cold','Respiratory infection',8),
(9,9,'Arthritis','Joint inflammation',9),
(10,10,'Allergic Reaction','Immune response',10);

INSERT INTO TREATMENT (Treatment_ID, Patient_ID, Treatment_Name, Dosage_Info, Cost) VALUES
(1,1,'Amlodipine','5mg daily',250.00),
(2,2,'Nitroglycerin','0.4mg as needed',400.00),
(3,3,'Oseltamivir','75mg twice daily',650.00),
(4,4,'Hydrocortisone Cream','Apply twice daily',300.00),
(5,5,'Physiotherapy','3 sessions weekly',1200.00),
(6,6,'Ibuprofen','400mg every 8 hours',200.00),
(7,7,'Metformin','500mg twice daily',350.00),
(8,8,'Vitamin C','500mg daily',150.00),
(9,9,'Diclofenac','50mg twice daily',250.00),
(10,10,'Antihistamine','10mg daily',180.00);

INSERT INTO CARE_PLAN (Care_Plan_ID, Treatment_ID, Diagnosis_ID, Start_Date, End_Date, Note) VALUES
(1,1,1,'2026-02-01','2026-08-01','Blood pressure control'),
(2,2,2,'2026-02-02','2026-03-02','Cardiac monitoring'),
(3,3,3,'2026-02-03','2026-02-10','Antiviral treatment'),
(4,4,4,'2026-02-04','2026-02-18','Skin treatment'),
(5,5,5,'2026-02-05','2026-03-20','Rehabilitation'),
(6,6,6,'2026-02-06','2026-02-13','Pain relief'),
(7,7,7,'2026-02-07','2026-08-07','Blood sugar control'),
(8,8,8,'2026-02-08','2026-02-15','Immune support'),
(9,9,9,'2026-02-09','2026-03-09','Joint pain management'),
(10,10,10,'2026-02-10','2026-02-20','Allergy treatment');

INSERT INTO APPT_PROCEDURE (Appt_Procedure_ID, Appointment_ID, Treatment_ID, Dosage, Duration) VALUES
(1,1,1,'5mg','180 Days'),
(2,2,2,'0.4mg','30 Days'),
(3,3,3,'75mg','7 Days'),
(4,4,4,'Twice Daily','14 Days'),
(5,5,5,'3 Sessions Weekly','45 Days'),
(6,6,6,'400mg','7 Days'),
(7,7,7,'500mg','180 Days'),
(8,8,8,'500mg','7 Days'),
(9,9,9,'50mg','30 Days'),
(10,10,10,'10mg','10 Days');

INSERT INTO USAGES (Usage_ID, Inventory_ID, Treatment_ID, Quantity_Used, Usage_Date) VALUES
(1,1,1,30,'2026-02-01'),
(2,2,2,10,'2026-02-02'),
(3,3,3,14,'2026-02-03'),
(4,4,4,2,'2026-02-04'),
(5,5,5,1,'2026-02-05'),
(6,6,6,21,'2026-02-06'),
(7,7,7,60,'2026-02-07'),
(8,8,8,14,'2026-02-08'),
(9,9,9,30,'2026-02-09'),
(10,10,10,10,'2026-02-10');

-- 3. Run Query Test
SELECT * FROM vw_patient_records WHERE patient_ID = 1;