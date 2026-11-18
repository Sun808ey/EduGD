# EduGuard: 180 Questions and Answers

This document combines product-level, administrator-dashboard, and stakeholder-pitch questions. Answers are based on the EduGuard frontend, backend, Android controller, API contracts, tests, and project documentation.

## Part I: EduGuard Product Questions

### Purpose and scope

1. **What is EduGuard?**\
   EduGuard is an academic proof-of-concept for enforcing phone-use policies on school-owned Android devices.

2. **Who is EduGuard for?**\
   It is designed for authorized administrators in Ugandan secondary schools.

3. **What problem does it solve?**\
   It helps schools define, apply, and review device-use rules, including when internet access is unreliable.

4. **Is EduGuard a commercial mobile-management platform?**\
   No. It is a proof-of-concept MVP, not a complete commercial MDM product.

5. **Which devices does it support?**\
   It targets managed school-owned Android devices, with documented support for Android 10-15, subject to physical verification.

6. **What can EduGuard manage?**\
   It manages schools, devices, policies, enrollment, synchronization, compliance, incidents, violations, and audit records.

7. **What are the main parts of the system?**\
   EduGuard includes an administrator dashboard, Flask API, PostgreSQL database, rate-limiting service, and Android device controller.

8. **Does the browser connect directly to the database?**\
   No. The browser communicates through the protected EduGuard API.

9. **Does EduGuard require constant internet access?**\
   No. The Android controller is designed to continue enforcing the last verified policy offline.

10. **Can EduGuard manage personal learner phones?**\
    No. Its intended scope is approved, school-owned Android devices.

### School and enrollment

11. **How does a school start using EduGuard?**\
    An administrator registers one school profile with its identity, contacts, location, and timezone.

12. **What is a device record?**\
    It is the school's record of a managed device, including its reference, Android details, enrollment, policy, status, and compliance information.

13. **Who creates the device identity?**\
    The managed Android device creates its canonical identity during enrollment rather than an administrator typing it manually.

14. **How is a device enrolled?**\
    An administrator issues a school-approved enrollment credential, which is used during the Android device-owner setup process.

15. **What is an enrollment token?**\
    It is a temporary pairing credential that authorizes one approved device to join the school's EduGuard environment.

16. **How long does an enrollment token last?**\
    The documented design gives it a ten-minute lifetime, and it can be used only once.

17. **Can enrollment use a QR code?**\
    Yes. The dashboard can generate a QR code containing the pairing information.

18. **What happens after enrollment?**\
    The device receives a separate credential for later authenticated communication and reports its capabilities and status.

19. **Can a device credential be revoked?**\
    Yes. Revocation prevents further authenticated device activity and requires re-enrollment.

20. **What device statuses are supported?**\
    Devices can be active, suspended, or retired, in addition to having enrollment and compliance states.

### Ownership and policies

21. **Can devices be assigned to classes or departments?**\
    Yes. EduGuard records responsibility for a class or department without permanently assigning a device to a learner.

22. **What is an EduGuard policy?**\
    A policy is a set of rules describing how a managed device may be used.

23. **What can a policy control?**\
    Policies can control applications, schedules, kiosk use, network behavior, screen locks, device restrictions, screen time, web domains, and offline behavior.

24. **What device-use modes are available?**\
    The system supports normal managed, dedicated learning, and examination modes.

25. **Can policies follow the school timetable?**\
    Yes. Policies can use recurring days and times based on the school's configured timezone.

26. **Can a policy approve or block applications?**\
    Yes. Administrators can select approved applications and block restricted ones from the school catalogue.

27. **Does EduGuard install applications?**\
    No. The catalogue identifies applications for policy purposes; it is not an app store or installation service.

28. **Can EduGuard restrict websites?**\
    Yes. The Android controller supports domain allowlists and blocklists through its filtering service.

29. **Does EduGuard enforce screen-time limits?**\
    The policy contract supports daily limits, reset times, and behavior after the limit is exhausted.

30. **Can policies target specific groups or devices?**\
    Yes. Policies can apply to selected classes, departments, or individual devices.

31. **Can an existing policy be edited?**\
    Existing revisions are immutable; changes create a new revision while preserving history.

32. **What policy statuses are supported?**\
    Policies can be draft, active, inactive, or revoked.

### Device enforcement

33. **How does a policy reach a device?**\
    The device requests its authorized state, verifies the signed policy, and activates it only after validation succeeds.

34. **What happens when the device is offline?**\
    It continues enforcing the last verified and successfully activated policy.

35. **How does the device know a policy is genuine?**\
    It verifies the policy signature, policy hash, revision data, and trusted signing key.

36. **What happens if a device lacks a required capability?**\
    Synchronization can be blocked instead of applying a policy the device cannot safely enforce.

37. **What does “fail closed” mean in EduGuard?**\
    It means the system refuses an unsafe or unverifiable change rather than silently weakening protection.

38. **Can an administrator temporarily block a device?**\
    Yes. Authorized administrators can create and clear device block overrides with a recorded reason.

39. **Can an administrator clear a device's policy?**\
    Yes. Clearing is an explicit recorded action and is not inferred merely because an assignment is missing.

40. **Can EduGuard roll back a policy?**\
    Yes. An older revision can be intentionally restored through the synchronization process.

41. **What is kiosk mode?**\
    Kiosk mode limits the device to approved applications and a controlled school-use experience.

42. **What other device restrictions are supported?**\
    Controls include restrictions on factory reset, Safe Mode, debugging, USB transfer, account changes, user switching, screenshots, camera, microphone, location, and network settings.

### Synchronization and monitoring

43. **What is the synchronization queue?**\
    It records policy or control delivery and shows whether the device has acknowledged the requested change.

44. **What does device acknowledgement mean?**\
    It means the device has confirmed that it received and processed the relevant policy or command.

45. **What synchronization states can administrators review?**\
    The interface distinguishes states such as pending, sent, applied, and failed.

46. **What does the dashboard show?**\
    It can show enrolled, compliant, non-compliant, offline-review, missing, managed, and enforcement-failure counts.

47. **Is an offline device automatically non-compliant?**\
    No. Offline status describes connectivity, while compliance depends on the device's reported enforcement state.

48. **Does the dashboard update continuously?**\
    It refreshes when requested or after completed actions; it is not presented as a continuously streaming monitor.

49. **What are violations?**\
    Violations are privacy-limited records of policy-related events, with device, time, policy, sequence, and hash information.

50. **What are incidents?**\
    Incidents are operational records that can move through statuses such as open, under review, action taken, and closed.

51. **What are audit logs used for?**\
    They provide an accountable history of authentication, enrollment, policy, synchronization, device, incident, and violation activity.

52. **Can reports be exported?**\
    Violation reports can be reviewed with filters and exported in CSV format.

### Security, privacy, and readiness

53. **How do administrators sign in?**\
    EduGuard uses named administrator accounts, protected sessions, expiry handling, logout, and server-side authorization.

54. **Does every administrator have the same access?**\
    No. Permissions are operation-specific, such as managing administrators, assigning policies, or revoking credentials.

55. **Are sensitive administrator actions protected?**\
    Yes. Actions such as password resets, permission changes, disabling accounts, and session revocation require additional verification and a reason.

56. **Where does the browser store login credentials?**\
    The administrator token is kept in memory only; reloading the page requires signing in again.

57. **How does EduGuard limit personal data collection?**\
    It excludes private messages, photos, contacts, health information, family information, location history, microphone recordings, and learner content.

58. **Does EduGuard store browsing history?**\
    No. Website-control evidence uses domain hashes and rule outcomes rather than storing URLs, paths, queries, or browsing history.

59. **Does EduGuard support local languages?**\
    The interface and translation workflow support English, Acholi, Lugbara, Ateso, Runyankole, and Luganda.

60. **Is EduGuard ready for full production deployment?**\
    Not yet. The repository identifies physical Android testing, hosted-service verification, deployment checks, and production-readiness gates as still requiring external confirmation.

## Part II: Administrator Dashboard Questions

### Authentication and access

61. **Where does an administrator sign in?**\
    At the `/login` page using a username and password.

62. **What happens after successful login?**\
    EduGuard creates a session, verifies the administrator identity, and opens protected dashboard pages.

63. **What happens when someone opens a protected page while signed out?**\
    They are redirected to login, and the requested page is preserved for after authentication.

64. **What happens when a session expires?**\
    EduGuard clears the session and asks the administrator to sign in again.

65. **Does refreshing the browser keep the administrator logged in?**\
    No. The session token is held in memory, so a page reload requires a new login.

66. **How does an administrator sign out?**\
    The dashboard requests server-side logout, then clears the local session and cached data.

67. **What happens after an incorrect password?**\
    The dashboard shows an authentication error without revealing sensitive details.

68. **What happens after too many failed logins?**\
    Login attempts are temporarily rate-limited and the screen shows when to retry.

69. **Who can access administrator routes?**\
    Only authenticated administrators can enter protected dashboard routes, and the backend checks each request.

70. **How do permissions affect the dashboard?**\
    Permissions determine which actions are visible and which operations the server will accept.

### School setup and dashboard navigation

71. **Where is the school profile created?**\
    Use `/school` during initial setup or `/settings` after the profile exists.

72. **What information is recorded for the school?**\
    EduGuard records the school name, district, type, contacts, location, authorized administrator, and timezone.

73. **Why is the school timezone important?**\
    It controls policy schedules and the interpretation of operational timestamps.

74. **What does the main dashboard show?**\
    It summarizes devices, enrollment, compliance, connectivity review, missing assets, violations, and enforcement issues.

75. **What is the Operations Overview page for?**\
    It brings school, device, policy, enrollment, synchronization, violation, audit, and catalogue information into one operational view.

76. **How does an administrator refresh dashboard information?**\
    Select the refresh action; EduGuard reloads the relevant records from the API.

77. **What happens when a dashboard metric is unavailable?**\
    The dashboard displays “Not reported” instead of guessing a value.

78. **Can administrators change the dashboard language or theme?**\
    Yes. The interface supports language selection and light or dark display modes.

79. **What does the Data Protection page explain?**\
    It explains what EduGuard records, what it excludes, and how privacy-limited evidence is handled.

80. **Where can an administrator see the full operating workflow?**\
    The Operations Overview and Enforcement Center connect the main administrative tasks.

### Device management and enrollment

81. **Where can administrators see all devices?**\
    Use the `/devices` page to view the school’s managed device register.

82. **What information appears in the device list?**\
    The list can show the device reference, model, enrollment state, policy state, connectivity, and compliance status.

83. **What does the device detail page show?**\
    It shows asset details, policy assignment, provisioning, compliance, controls, evidence, violations, and incident history.

84. **How is a new device added?**\
    An administrator issues an enrollment credential; the Android device then creates its managed identity during setup.

85. **How is an enrollment token issued?**\
    In `/provisioning`, select the school, an active policy revision, an optional device, and provide a reason.

86. **Is the pairing token stored by the browser?**\
    No. It is displayed once and is not persisted by the frontend.

87. **Can the administrator use a QR code for enrollment?**\
    Yes. The dashboard can convert the temporary pairing information into an Android provisioning QR code.

88. **Can an enrollment token be revoked?**\
    Yes. An active token can be revoked with a recorded reason before it is used.

89. **Can an enrolled device be disconnected from EduGuard?**\
    Yes. An authorized administrator can revoke its active credential, after which the device must enroll again.

90. **Can devices be assigned to classes or departments?**\
    Yes. The assignment workflow records responsibility, expected return, and issue or return condition.

### Policy management

91. **Where are applications and domains managed?**\
    Use `/policies/catalogue` to maintain approved applications and managed web domains.

92. **What is the difference between enabled and disabled catalogue entries?**\
    Enabled entries can be selected for new policies; disabled entries remain available for historical context.

93. **How is a policy created?**\
    Use `/policies/new` to enter the policy name, code, description, dates, scope, and controls.

94. **What controls can an administrator configure?**\
    The form supports applications, schedules, kiosk mode, network rules, device restrictions, screen locks, web filtering, and screen-time limits.

95. **What operating modes can be selected?**\
    The dashboard supports normal managed, dedicated learning, and examination device modes.

96. **Can a policy run only during school hours?**\
    Yes. Select recurring days, start time, end time, and the school timezone.

97. **Can administrators block selected applications?**\
    Yes. Applications are selected from the school catalogue and blocked by their managed package identity.

98. **Can administrators define website rules?**\
    Yes. Managed domains can be allowed or blocked, including selected subdomains.

99. **Does the policy form show what will happen before saving?**\
    Yes. It provides a plain-language preview of the selected controls.

100. **What happens when a policy is saved?**\
     The server validates the complete policy and creates an immutable first revision.

### Assignment, enforcement, and synchronization

101. **How is a policy assigned to a device?**\
     Select an exact policy revision, provide a reason, and submit the assignment from the policy or device workflow.

102. **Can a policy assignment be cleared?**\
     Yes. Clearing is a separate recorded action and requires the correct permission and reason.

103. **How does an administrator know whether a policy reached the device?**\
     Review the `/sync` queue for delivery and acknowledgement information.

104. **What synchronization states can be reviewed?**\
     Common states include pending, sent, applied, and failed.

105. **What does device acknowledgement mean?**\
     It means the device confirmed that it received and processed the policy or command.

106. **What happens if the device is offline?**\
     The Android controller continues using its last verified policy and synchronizes later.

107. **What is the Enforcement Center used for?**\
     It provides shortcuts to policy assignment, device controls, synchronization, violations, and audit evidence.

108. **Can an administrator block a device immediately?**\
     Yes. An authorized administrator can create a persistent block override with a reason.

109. **Can the block override be removed?**\
     Yes. The same device-control workflow can clear the override and record the action.

110. **What evidence is shown for device enforcement?**\
     The dashboard can show policy application, usage, web-filter, and block-override evidence without exposing private content.

### Compliance, violations, and audit review

111. **What does “compliant” mean on the dashboard?**\
     It means the backend received a healthy current policy-enforcement state from the device.

112. **Does being offline automatically make a device non-compliant?**\
     No. Offline is a connection state, while compliance depends on reported enforcement results.

113. **What should an administrator inspect when a device is non-compliant?**\
     Review its enforcement status, last compliance check, failed controls, synchronization state, and recent evidence.

114. **Where are violations reviewed?**\
     Use the `/reports` page or the violation section on an individual device.

115. **How can violation records be filtered?**\
     Filter by device, class, start date, and end date.

116. **What types of violations can appear?**\
     Examples include blocked applications, kiosk bypass attempts, restricted-setting changes, web-filter blocks, and enforcement failures.

117. **What information is shown for each violation?**\
     The record shows when it occurred, the device or class, violation type, outcome, policy, rule, and privacy-safe details.

118. **What do the sequence number and event hash mean?**\
     They help verify the order and integrity of the evidence; they are not learner-content records.

119. **Can violation results be exported?**\
     Yes. Administrators can export the currently filtered violation results as a CSV file.

120. **What is the complete administrator workflow?**\
     Sign in, configure the school, maintain the catalogue, create policies, enroll devices, assign revisions, monitor synchronization, review compliance, investigate violations, and confirm the audit history.

## Part III: Stakeholder Pitch Questions

### The problem and the idea

121. **What is EduGuard?**\
     EduGuard is a school system for managing how school-owned Android phones are used for learning.

122. **Why is EduGuard needed in Uganda?**\
     Many schools need phones for learning but also need clear rules to reduce misuse and distractions.

123. **Who is EduGuard made for?**\
     It is made for Ugandan secondary schools that provide or manage Android devices.

124. **What problem does EduGuard solve?**\
     It helps schools create phone-use rules, apply them, and check whether the rules are being followed.

125. **Why does EduGuard focus on school-owned devices?**\
     School-owned devices are under the school's responsibility and can be managed with clear school approval.

126. **Is EduGuard simply a way of banning phones?**\
     No. It helps schools allow useful learning activities while limiting harmful or distracting use.

127. **How can EduGuard support learning?**\
     It can allow approved learning applications and resources while restricting unrelated applications during school activities.

128. **Who decides the phone-use rules?**\
     The school decides the rules, and authorized administrators enter them into EduGuard.

129. **Who benefits from EduGuard?**\
     Schools get better control, teachers get clearer rules, learners get safer devices, and parents get more confidence.

130. **What happens when internet access is poor?**\
     The device can continue using the last approved rule and send updates when it connects again.

### How the system works

131. **How does EduGuard work in simple terms?**\
     The school creates rules in the dashboard, the phone receives them, and the system reports the phone's status.

132. **What is the administrator dashboard?**\
     It is the school's control centre for devices, rules, enrollment, reports, and security records.

133. **What does the Android part do?**\
     It applies the school's approved rules directly on the managed device.

134. **What does the central system do?**\
     It stores school records, sends approved policies, receives device updates, and keeps reviewable records.

135. **Does the device need internet all the time?**\
     No. It is designed to enforce the last verified policy even when it is temporarily offline.

136. **How does the device update the school?**\
     It sends its status, policy result, and selected security events when a connection is available.

137. **What types of rules can the school create?**\
     Rules can cover approved applications, blocked applications, schedules, screen time, network use, and device restrictions.

138. **Can the school block certain applications?**\
     Yes. The school can block applications such as games or social media when they are not allowed.

139. **Can the school control websites and screen time?**\
     Yes. EduGuard supports approved or blocked domains and daily screen-time rules.

140. **How does EduGuard know whether a device is compliant?**\
     The device reports whether it has applied the required policy and whether any controls have failed.

### Privacy and security

141. **What information does EduGuard collect?**\
     It collects school asset details, device status, policy information, compliance results, and security events.

142. **Does EduGuard read private messages or photos?**\
     No. The system is designed not to collect private messages, photos, contacts, or learner content.

143. **Does EduGuard store browsing history?**\
     No. It records limited web-control evidence, such as a blocked-domain result, not a learner's browsing history.

144. **How does EduGuard stop unauthorized people from using the dashboard?**\
     Administrators must sign in, and each important action requires the correct permission.

145. **How are devices identified?**\
     The managed device creates a secure identity during enrollment instead of relying only on a name typed by a person.

146. **Can someone secretly change a policy?**\
     Important changes are linked to an administrator, a reason, and a recorded policy version.

147. **How are security records protected?**\
     EduGuard uses controlled access, signed device communication, protected credentials, and records that can be checked later.

148. **What happens if a device is lost or stolen?**\
     The school can suspend or retire the device and revoke its access credential.

149. **Can the school remove old records?**\
     Yes. Retention and deletion must follow the school's approved record-keeping period and protection rules.

150. **Is EduGuard legally safe to use immediately?**\
     The system follows documented data-minimisation principles, but the school must still approve its privacy, safeguarding, and data-governance arrangements before live use.

### School operations

151. **How does a school begin using EduGuard?**\
     The administrator registers the school profile, creates a policy, and prepares approved school-owned devices.

152. **How is a device enrolled?**\
     The administrator creates a short-lived pairing token or QR code, then uses it during approved Android setup.

153. **What happens if an enrollment token expires or is lost?**\
     The old token is no longer used, and the administrator creates a new one.

154. **How are administrators controlled?**\
     The school can create named administrators and give each person only the permissions needed for their work.

155. **What happens when a learner breaks a device rule?**\
     EduGuard records the policy event for review; it does not automatically decide punishment.

156. **Can an administrator block a device?**\
     Yes. An authorized administrator can place a recorded block on a device and remove it later if appropriate.

157. **What happens when a device is not compliant?**\
     The administrator reviews the failed controls, last update, policy assignment, and recent evidence before taking action.

158. **Can one device be shared by different classes?**\
     Yes. The school can record the responsible class or department and track issue and return details.

159. **What reports can the school review?**\
     The school can review device status, policy changes, violations, synchronization, audit events, and privacy-safe evidence.

160. **Does EduGuard support Ugandan languages?**\
     The dashboard supports English, Acholi, Lugbara, Ateso, Runyankole, and Luganda translation options.

### Project readiness and cost

161. **What is the current stage of EduGuard?**\
     The dashboard, backend services, policy workflows, and security design are developed as a proof-of-concept.

162. **Is EduGuard ready for national rollout today?**\
     No. It still needs wider field testing, live service checks, and physical Android verification.

163. **What has already been tested?**\
     The project includes automated tests for authentication, policies, devices, security rules, database behavior, and dashboard workflows.

164. **What still needs to be verified?**\
     The team must verify real device-owner setup, offline behavior, reboot recovery, different phone models, and full production operation.

165. **Will EduGuard work on every Android phone?**\
     No. It targets supported Android versions and approved device models that must be tested before use.

166. **What is needed for a school pilot?**\
     The pilot needs approved school-owned devices, trained administrators, an agreed policy, a test period, and a clear support plan.

167. **Does the dashboard work if the backend service is temporarily unavailable?**\
     The device keeps its last approved local policy, while administrative updates wait until the service returns.

168. **How much does EduGuard cost?**\
     The current project is planned around free-tier resources, but final running costs depend on the number of schools, devices, and records.

169. **Can EduGuard grow beyond one school?**\
     The design can be extended, but large-scale use needs separate testing, stronger operations, and a confirmed cost plan.

170. **Who will maintain EduGuard after the project?**\
     A named school, education body, or support team must take responsibility for updates, security, training, and technical support.

### Stakeholder concerns and future plans

171. **How will the school measure success?**\
     It can compare policy compliance, rule violations, device availability, learning use, and feedback from teachers and learners.

172. **How should the first pilot be run?**\
     Start with a small number of devices, use agreed rules, collect feedback, and review safety and learning results before expanding.

173. **How will learner rights be protected?**\
     The school should explain the rules clearly, collect only necessary information, limit access, and provide a fair way to raise concerns.

174. **Can a learner or parent question a rule?**\
     Yes. The school should handle questions through its normal safeguarding and school-governance process; EduGuard only records and applies approved rules.

175. **Does EduGuard replace teachers or school leaders?**\
     No. It supports their work but does not replace human judgment, teaching, discipline, or safeguarding decisions.

176. **Can the school change its rules later?**\
     Yes. A new policy version can be created while the previous version remains available for history.

177. **What if the wrong device is blocked?**\
     The administrator can review the reason, correct the record, clear the block when authorized, and keep the action in the audit history.

178. **What is the most important limitation of EduGuard?**\
     It cannot guarantee perfect control on every phone, so physical testing and responsible school supervision remain necessary.

179. **Why should stakeholders support EduGuard?**\
     It offers a local, privacy-conscious way for schools to use learning devices while keeping clear control and accountability.

180. **What is the short pitch for EduGuard?**\
     EduGuard helps Ugandan schools use school-owned Android devices for learning while applying clear rules, protecting privacy, working during poor internet, and keeping records that can be checked later.
