// import { useState, useContext } from "react";
// import { AuthContext } from "../context/AuthContext";
// import { useNavigate, Link } from "react-router-dom";

// const Register = () => {
//   const { register } = useContext(AuthContext);
//   const navigate = useNavigate();
//   const [form, setForm] = useState({ username: "", password: "" });
//   const [error, setError] = useState("");

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     try {
//       await register(form);
//       navigate("/login");
//     } catch (err) {
//       setError("Registration failed. Try a different username.");
//     }
//   };

//   return (
//     <div className="flex justify-center mt-20">
//       <form onSubmit={handleSubmit} className="bg-white p-6 shadow rounded w-80">
        
//         <h2 className="text-xl mb-4">Create Account</h2>

//         {error && (
//           <p className="text-red-500 text-sm mb-3">{error}</p>
//         )}

//         <input
//           type="text"
//           placeholder="Username"
//           className="w-full border p-2 mb-3"
//           onChange={(e) => setForm({ ...form, username: e.target.value })}
//         />

//         <input
//           type="password"
//           placeholder="Password"
//           className="w-full border p-2 mb-3"
//           onChange={(e) => setForm({ ...form, password: e.target.value })}
//         />

//         <button className="bg-green-500 text-white w-full p-2 rounded">
//           Register
//         </button>

//         <p className="mt-3 text-sm">
//           Already have an account?{" "}
//           <Link to="/login" className="text-blue-500">Login</Link>
//         </p>

//       </form>
//     </div>
//   );
// };

// export default Register;