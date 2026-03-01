// import { useState } from "react";
// import API from "../services/api";
// import { useNavigate } from "react-router-dom";

// function Login() {
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const navigate = useNavigate();

//   const loginUser = async () => {
//     try {
//       const res = await API.post("token/", {
//         username,
//         password,
//       });

//       localStorage.setItem("token", res.data.access);
//       navigate("/dashboard");
//     } catch {
//       alert("Invalid Credentials");
//     }
//   };

//   return (
//     <div style={{ padding: "50px" }}>
//       <h2>Login</h2>
//       <input placeholder="Username" onChange={(e) => setUsername(e.target.value)} />
//       <br /><br />
//       <input type="password" placeholder="Password" onChange={(e) => setPassword(e.target.value)} />
//       <br /><br />
//       <button onClick={loginUser}>Login</button>
//     </div>
//   );
// }

// export default Login;