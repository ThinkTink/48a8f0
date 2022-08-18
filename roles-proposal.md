1. We can make 3 more models/tables and 1 extra field in UserPost. The first model is `Role`, where we define roles like `Owner`, `Editors` and `Viewer`. For the permission, we can create the second model called `Permission` and add all possible permission that an user can have with a post. Next, we create an intermediate model/table called RolePermission that allows matching a role with one or more permissions. Furthermore, in the `UserPost`, we just need to add a field which is the foreign key from the table `Role`.

2. With the new setup, I will join the result from `UserPost` (when checking with user ID and post ID) with the `Role` table and check whether or not the role is either an `Owner` or `Editor` or any other roles that have the permission to change the post.

Note: Since I request a reset on the assessment, I would write the amount of time it took me to complete the assessment. The total time spent on the assessment is about 6 hours.
